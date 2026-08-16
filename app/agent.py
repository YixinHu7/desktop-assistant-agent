import json
import os
from typing import Any, Optional
from openai import OpenAI

from app.memory import MemoryStore
from app.router import Router
from app.logger import log_event
from app.executor import ToolExecutor
from app.tools.registry import build_tool_definitions, get_tool_schemas
from app.planner import Planner
from app.reviewer import ExecutionReviewer
from app.replanner import Replanner
from app.recovery import ToolRecoveryManager
from app.memory_policy import MemoryPolicy
from app.approval_policy import ApprovalPolicy
from app.tool_use_policy import ToolUsePolicy
from app.run_context import RunContext
from app.metrics import compute_run_metrics
from app.config import config
from app.skills import SkillRegistry, SkillSelector


class DesktopAssistantAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing")
        
        self.client = OpenAI(api_key=api_key)
        self.memory = MemoryStore()
        self.router = Router(self.client)
        
        self.tool_definitions = build_tool_definitions(self.memory)
        self.tools = get_tool_schemas(self.tool_definitions)
        self.executor = ToolExecutor(self.tool_definitions)
        
        self.planner = Planner(self.client)
        self.reviewer = ExecutionReviewer(self.client)
        self.replanner = Replanner(self.client)
        self.recovery = ToolRecoveryManager()
        self.memory_policy = MemoryPolicy(self.client)
        self.approval_policy = ApprovalPolicy(self.tool_definitions)
        self.tool_use_policy = ToolUsePolicy(self.client)
        self.skill_registry = SkillRegistry(config.skills_dir) if config.enable_skills else None
        self.skill_selector = (
            SkillSelector(self.client, self.skill_registry)
            if self.skill_registry is not None
            else None
        )
        self.last_run_summary: Optional[dict[str, Any]] = None
        
        self.system_prompt = (
            "You are a concise desktop assistant agent. "
            "Be helpful, practical, and operationally clear. "
            "Use tools when they are genuinely useful. "
            "Do not invent tool results. "
            "When a plan is provided, use it to guide execution step by step. "
            "Only mark progress that is supported by available evidence."
        )
    
    
    def _finalize_run(
        self,
        run: RunContext,
        final_answer: str,
        used_tools: list[str],
    ) -> str:
        self.memory.add_history(
            "assistant",
            final_answer,
        )

        log_event(
            "final_answer",
            {
                "text": final_answer,
                "used_tools": used_tools,
            },
        )

        run.final_answer = final_answer
        run_summary = run.to_summary()

        self.last_run_summary = run_summary

        log_event(
            "run_summary",
            run_summary,
        )

        run_metrics = compute_run_metrics(run_summary)

        log_event(
            "run_metrics",
            run_metrics,
        )

        return final_answer
    
    
    def _run_execution_cycle(
        self,
        route,
        memory_context: str,
        plan_text: str,
        recent_history:list,
        tool_use_decision=None,
        skill_instruction: str | None = None,
        run: RunContext = None,
    ):
        execution_instruction = (
            "If tools are useful, you may use them to make progress on the user's request. "
            "For complex requests, work through the plan step by step. "
            "Do not claim a step is completed unless it is supported by available tool results. "
            "If a step cannot be completed with current tools, say so clearly."
        )
        
        if route.route == "plan":
            execution_instruction = (
                "You are in execution mode for a planned task. "
                "Use the provided plan to guide your actions. "
                "Prefer making concrete progress with tools when possible. "
                "Track which steps are completed based on actual tool outputs. "
                "Do not pretend you completed a step without evidence. "
                "If some steps cannot be completed with the available tools, explain that clearly."
            )
        
        input_items = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "system",
                "content": f"Memory context:\n{memory_context}"
            },
            {
                "role": "system",
                "content": f"Routing decision: {route.route}. Reason: {route.reason}"
            },
            {
                "role": "system",
                "content": f"Plan context:\n{plan_text}"
            },
            {
                "role": "system",
                "content": execution_instruction
            }
        ]
        
        if tool_use_decision is not None:
            input_items.append({
                "role": "system",
                "content": (
                    "Tool-use policy:\n"
                    f"- should_use_tools: {tool_use_decision.should_use_tools}\n"
                    f"- likely_tools: {tool_use_decision.likely_tools}\n"
                    f"- avoid_tools: {tool_use_decision.avoid_tools}\n"
                    f"- requires_grounding: {tool_use_decision.requires_grounding}\n"
                    f"- reason: {tool_use_decision.reason}\n\n"
                    "Follow this policy when deciding whether to call tools. "
                    "If should_use_tools is false, avoid tool calls unless absolutely necessary. "
                    "If likely_tools are provided, prefer those tools when tool use is needed."
                )
            })
        
        if tool_use_decision is not None and tool_use_decision.requires_grounding:
            input_items.append({
                "role": "system",
                "content": (
                    "Grounding instruction: This task involves files, directories, repository structure, "
                    "or uncertain local paths. Do not invent paths such as './project'. "
                    "If no exact path has been confirmed, first call list_files with path='.'. "
                    "Only call read_file after there is evidence that the file exists."
                )
            })
        
        if skill_instruction:
            input_items.append({
                "role": "system",
                "content": skill_instruction
            })
        
        for msg in recent_history:
            input_items.append(msg)
        
        used_tools = []
        tool_results_for_summary = []
        
        tools_for_this_turn = self.tools

        # If tool use decision gives result as should not use tools
        if tool_use_decision is not None and not tool_use_decision.should_use_tools:
            tools_for_this_turn = []
        
        response = self.client.responses.create(
            model=config.model,
            input=input_items,
            tools=tools_for_this_turn,
            parallel_tool_calls=False
        )
        
        while True:
            function_calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]

            # No more tools need to execute
            if not function_calls:
                final_answer = response.output_text.strip() or "Done."
                return final_answer, used_tools, tool_results_for_summary
            
            tool_outputs = []
            
            for call in function_calls:
                arguments = json.loads(call.arguments) if call.arguments else {}
                
                # Record the used tools
                used_tools.append(call.name)
                
                approved = self._ask_for_approval(
                    tool_name=call.name,
                    arguments=arguments,
                    run=run,
                    source="primary",
                )
                
                if not approved:
                    result = {
                        "ok": False,
                        "error": "User denied approval",
                        "metadata": {
                            "tool": call.name,
                            "denied": True,
                        },
                    }
                    tool_status = "denied"
                else:
                    result = self.executor.execute(call.name, arguments)
                    
                    tool_status = (
                        "completed"
                        if result.get("ok", False)
                        else "failed"
                    )
                
                tool_call_payload = {
                    "tool": call.name,
                    "arguments": arguments,
                    "kind": "primary",
                    "status": tool_status,
                    "result": result,
                }
                
                if run is not None:
                    run.tool_calls.append(tool_call_payload)
                
                log_event("tool_call", tool_call_payload)
                
                tool_results_for_summary.append({
                    "tool_name": call.name,
                    "arguments": arguments,
                    "result": result,
                    "kind": "primary",
                    "recovered": False,
                })
                
                final_tool_result = result
                
                # Do not attempt recovery when the user denied approval.
                recovery_decision = {
                    "should_retry": False,
                    "retry_tool": None,
                    "retry_arguments": {},
                    "reason": "",
                }
                
                if approved:
                    recovery_decision = self.recovery.maybe_recover(
                        call.name,
                        arguments,
                        result,
                    )
                    
                if recovery_decision["should_retry"]:
                    retry_tool = recovery_decision["retry_tool"]
                    retry_arguments = recovery_decision["retry_arguments"]
                    
                    recovery_attempt_payload = {
                        "type": "attempt",
                        "original_tool": call.name,
                        "original_arguments": arguments,
                        "original_result": result,
                        "retry_tool": retry_tool,
                        "retry_arguments": retry_arguments,
                        "reason": recovery_decision["reason"],
                    }
                    if run is not None:
                        run.recovery_events.append(recovery_attempt_payload)

                    log_event("tool_recovery_attempt", recovery_attempt_payload)
                    
                    retry_approved = self._ask_for_approval(
                        tool_name=retry_tool,
                        arguments=retry_arguments,
                        run=run,
                        source="recovery",
                    )
                    
                    if not retry_approved:
                        retry_result = {
                            "ok": False,
                            "error": "User denied recovery tool approval",
                            "metadata": {
                                "tool": retry_tool,
                                "denied": True,
                            },
                        }
                        retry_status = "denied"
                    else:
                        retry_result = self.executor.execute(
                            retry_tool,
                            retry_arguments,
                        )

                        retry_status = (
                            "completed"
                            if retry_result.get("ok", False)
                            else "failed"
                        )
                    
                    # Recovery tool calls must also be included in used_tools.
                    used_tools.append(retry_tool)

                    recovery_tool_call_payload = {
                        "tool": retry_tool,
                        "arguments": retry_arguments,
                        "kind": "recovery",
                        "recovery_for": call.name,
                        "status": retry_status,
                        "result": retry_result,
                    }
                    
                    if run is not None:
                        run.tool_calls.append(
                            recovery_tool_call_payload
                        )

                    log_event(
                        "tool_call",
                        recovery_tool_call_payload,
                    )
                    
                    tool_results_for_summary.append({
                        "tool_name": retry_tool,
                        "arguments": retry_arguments,
                        "result": retry_result,
                        "kind": "recovery",
                        "recovery_for": call.name,
                        "recovered": retry_result.get(
                            "ok",
                            False,
                        ),
                    })
                    
                    recovery_result_payload = {
                        "type": "result",
                        "original_tool": call.name,
                        "retry_tool": retry_tool,
                        "retry_arguments": retry_arguments,
                        "retry_result": retry_result,
                        "approved": retry_approved,
                        "success": retry_result.get(
                            "ok",
                            False,
                        ),
                    }
                    
                    if run is not None:
                        run.recovery_events.append(
                            recovery_result_payload
                        )

                    log_event(
                        "tool_recovery_result",
                        recovery_result_payload,
                    )
                    
                    final_tool_result = {
                        "original_failure": {
                            "tool_name": call.name,
                            "arguments": arguments,
                            "result": result,
                        },
                        "recovery_attempt": {
                            "tool_name": retry_tool,
                            "arguments": retry_arguments,
                            "result": retry_result,
                            "reason": recovery_decision["reason"],
                        },
                    }
                    
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(final_tool_result, ensure_ascii=False)
                })

            
            response = self.client.responses.create(
                model=config.model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools_for_this_turn,
                parallel_tool_calls=False
            )     
    
    
    def _ask_for_approval(
        self,
        tool_name: str,
        arguments: dict,
        run: Optional[RunContext] = None,
        source: str = "primary",
    ) -> bool:
        decision = self.approval_policy.decide(
            tool_name,
            arguments,
        )

        if decision.required:
            print("\n[Approval Required]")
            print(f"Tool: {tool_name}")
            print(f"Arguments: {arguments}")
            print(f"Risk: {decision.risk_level}")
            print(f"Reason: {decision.reason}")

            answer = input(
                "Approve? (y/n): "
            ).strip().lower()

            approved = answer == "y"
        else:
            approved = True

        approval_payload = {
            "tool": tool_name,
            "arguments": arguments,
            "required": decision.required,
            "approved": approved,
            "risk_level": decision.risk_level,
            "reason": decision.reason,
            "source": source,
        }

        if run is not None:
            run.approval_decisions.append(
                approval_payload
            )

        log_event(
            "approval_decision",
            approval_payload,
        )

        return approved
    
    
    def handle_user_message(self, user_input: str) -> str:
        self.last_run_summary = None

        run = RunContext(user_input=user_input)
        
        self.memory.add_history("user", user_input)
        
        memory_context = self.memory.get_context_text()
        
        # Get memory decision
        memory_decision = self.memory_policy.decide(user_input, memory_context)
        run.memory_decision = memory_decision.model_dump()
        log_event("memory_decision", memory_decision.model_dump())
        
        if memory_decision.action == "write" and memory_decision.key and memory_decision.value:
            self.memory.data["facts"][memory_decision.key] = memory_decision.value
            self.memory.save()

            log_event("memory_write", {
                "key": memory_decision.key,
                "value": memory_decision.value,
                "reason": memory_decision.reason,
                "source": "memory_policy"
            })
            # Update memory context
            memory_context = self.memory.get_context_text()
        
        # Get route decision
        route = self.router.decide(user_input, memory_context)
        run.route_decision = route.model_dump()
        log_event("route_decision", route.model_dump())
        
        # Get tool use decision
        tool_use_decision = self.tool_use_policy.decide(
            user_input=user_input,
            route=route.route,
            memory_context=memory_context,
        )

        run.tool_use_decision = tool_use_decision.model_dump()
        log_event("tool_use_decision", tool_use_decision.model_dump())
        
        # Get skill decision
        skill_decision = None
        selected_skill = None
        skill_instruction = None
        
        if self.skill_selector is not None:
            skill_decision = self.skill_selector.decide(user_input)
            log_event("skill_decision", skill_decision.model_dump())

            if skill_decision.should_use_skill and skill_decision.selected_skill:
                selected_skill = self.skill_registry.get_skill(skill_decision.selected_skill)

                if selected_skill:
                    skill_instruction = (
                        f"Selected skill: {selected_skill.name}\n"
                        f"Skill description: {selected_skill.description}\n"
                        f"Skill instructions:\n{selected_skill.instructions}"
                    )
            
        if skill_decision is not None:
            run.skill_decision = skill_decision.model_dump()

        if selected_skill is not None:
            run.selected_skill = selected_skill.name
            
            
        plan_goal = user_input
        # If route decision is "Plan"
        plan_text = "No explicit plan created."
        
        if route.route == "plan":
            plan = self.planner.make_plan(user_input, memory_context)
            plan_goal = plan.goal
            log_event("plan_created", plan.model_dump())
            run.plan = plan.model_dump()
            
            formatted_steps = []
            for i, step in enumerate(plan.steps, start=1):
                formatted_steps.append(f"{i}. {step.step}")
            
            plan_text = f"Goal: {plan.goal}\n" + "\n".join(formatted_steps)
        
        recent_history = self.memory.get_recent_history()

        final_answer, used_tools, tool_results_for_summary = self._run_execution_cycle(
            route=route,
            memory_context=memory_context,
            plan_text=plan_text,
            recent_history=recent_history,
            tool_use_decision=tool_use_decision,
            skill_instruction=skill_instruction,
            run=run,
        )
        
        execution_review = None
        replan_decision = None
        
        if route.route == "plan":
            tool_results_text = json.dumps(tool_results_for_summary, ensure_ascii=False, indent=2)

            execution_review = self.reviewer.review_execution(
                goal=plan_goal,
                plan_text=plan_text,
                tool_results_text=tool_results_text
            )
            log_event("step_review", execution_review.model_dump())
            run.step_review = execution_review.model_dump()

            has_remaining = len(execution_review.remaining_steps) > 0
            
            if has_remaining:
                replan_decision = self.replanner.replan(
                    user_input=user_input,
                    original_goal=plan_goal,
                    plan_text=plan_text,
                    tool_results_text=tool_results_text,
                    step_review_text=json.dumps(execution_review.model_dump(), ensure_ascii=False, indent=2),
                    memory_context=memory_context,
                )
                log_event("replan_decision", replan_decision.model_dump())
                run.replan_decision = replan_decision.model_dump()
                
        if replan_decision is not None and replan_decision.should_replan and len(replan_decision.next_steps) > 0:
            revised_steps = []
            for i, step in enumerate(replan_decision.next_steps, start=1):
                revised_steps.append(f"{i}. {step.step}")
            
            revised_plan_text = (
                f"Goal: {replan_decision.revised_goal}\n" + "\n".join(revised_steps)
            )
            
            revised_plan_payload = {
                "goal": replan_decision.revised_goal,
                "steps": [s.step for s in replan_decision.next_steps]
            }

            run.revised_plan = revised_plan_payload
            log_event("revised_plan_created", revised_plan_payload)
            
            second_answer, second_used_tools, second_tool_results = self._run_execution_cycle(
                route=route,
                memory_context=memory_context,
                plan_text=revised_plan_text,
                recent_history=self.memory.get_recent_history(),
                tool_use_decision=tool_use_decision,
                skill_instruction=skill_instruction,
                run=run,
            )
            
            used_tools.extend(second_used_tools)
            tool_results_for_summary.extend(second_tool_results)
            
            final_answer = (
                final_answer
                + "\n\nAfter reviewing the remaining work, I continued with a revised plan.\n"
                + second_answer
            )
        
        if replan_decision is not None and not replan_decision.should_replan:
            final_answer += (
                "\n\nI made the progress I could with the currently available tools, "
                f"but some remaining steps are still pending. {replan_decision.reason}"
            )
        
        recovery_attempted = any(item.get("kind") == "recovery" for item in tool_results_for_summary)
        recovery_succeeded = any(
            item.get("kind") == "recovery" and item.get("result", {}).get("ok", False)
            for item in tool_results_for_summary
        )
        
        if recovery_attempted and recovery_succeeded and "I could not" in final_answer:
            final_answer += (
                "\n\nA recovery step succeeded after the initial tool failure, "
                "so the agent was able to regain useful context."
            )

        log_event("execution_summary", {
            "route": route.route,
            "plan": plan_text,
            "used_tools": used_tools,
            "tool_results_count": len(tool_results_for_summary),
            "has_step_review": execution_review is not None,
            "has_replan_decision": replan_decision is not None,
            "replan_triggered": replan_decision.should_replan if replan_decision else False,
            "revised_plan_used": replan_decision.revised_goal if replan_decision and replan_decision.should_replan else None,
            "recovery_attempted": recovery_attempted,
            "recovery_succeeded": recovery_succeeded,
        })
            
        return self._finalize_run(
            run=run,
            final_answer=final_answer,
            used_tools=used_tools,
        )
        