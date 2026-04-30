import json
import os
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
        self.approval_policy = ApprovalPolicy()
        
        self.system_prompt = (
            "You are a concise desktop assistant agent. "
            "Be helpful, practical, and operationally clear. "
            "Use tools when they are genuinely useful. "
            "Do not invent tool results."
            "When a plan is provided, use it to guide execution step by step. "
            "Only mark progress that is supported by available evidence."
        )
    
    def _run_execution_cycle(
        self,
        route,
        memory_context: str,
        plan_text: str,
        recent_history:list,
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
        
        for msg in recent_history:
            input_items.append(msg)
        
        used_tools = []
        tool_results_for_summary = []
        
        response = self.client.responses.create(
            model="gpt-4.1-mini",
            input=input_items,
            tools=self.tools,
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
                
                if not self._ask_for_approval(call.name, arguments):
                    result = {"ok": False, "error": "User denied approval"}
                else:
                    result = self.executor.execute(call.name, arguments)
                
                log_event("tool_call", {
                    "tool_name": call.name,
                    "arguments": arguments,
                    "result": result
                })
                
                # Record the tool results
                tool_results_for_summary.append({
                    "tool_name": call.name,
                    "arguments": arguments,
                    "result": result,
                    "kind": "primary",
                    "recovered": False,
                })
                
                final_tool_result = result
                
                # Try deterministic recovery if the tool failed
                recovery_decision = self.recovery.maybe_recover(call.name, arguments, result)
                
                if recovery_decision["should_retry"]:
                    retry_tool = recovery_decision["retry_tool"]
                    retry_arguments = recovery_decision["retry_arguments"]
                    
                    log_event("tool_recovery_attempt", {
                        "original_tool": call.name,
                        "original_arguments": arguments,
                        "original_result": result,
                        "retry_tool": retry_tool,
                        "retry_arguments": retry_arguments,
                        "reason": recovery_decision["reason"],
                    })
                    
                    retry_result = self.executor.execute(retry_tool, retry_arguments)
                    
                    tool_results_for_summary.append({
                        "tool_name": retry_tool,
                        "arguments": retry_arguments,
                        "result": retry_result,
                        "kind": "recovery",
                        "recovery_for": call.name,
                        "recovered": retry_result.get("ok", False),
                    })
                    
                    log_event("tool_recovery_result", {
                        "retry_tool": retry_tool,
                        "retry_arguments": retry_arguments,
                        "retry_result": retry_result,
                    })
                    
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
                        }
                    }
                    
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(final_tool_result, ensure_ascii=False)
                })

            
            response = self.client.responses.create(
                model="gpt-4.1-mini",
                previous_response_id=response.id,
                input=tool_outputs,
                tools=self.tools,
                parallel_tool_calls=False
            )     
    
    def _ask_for_approval(self, tool_name: str, arguments: dict) -> bool:
        decision = self.approval_policy.decide(tool_name, arguments)
        
        log_event("approval_decision", {
            "tool_name": tool_name,
            "arguments": arguments,
            "required": decision.required,
            "risk_level": decision.risk_level,
            "reason": decision.reason,
        })
        
        if not decision.required:
            return True
        
        print(f"\n[Approval Required]")
        print(f"Tool: {tool_name}")
        print(f"Arguments: {arguments}")
        print(f"Risk: {decision.risk_level}")
        print(f"Reason: {decision.reason}")
        
        answer = input("Approve? (y/n): ").strip().lower()
        return answer == "y"
    
    def handle_user_message(self, user_input: str) -> str:
        self.memory.add_history("user", user_input)
        
        memory_context = self.memory.get_context_text()
        
        # Get memory decision
        memory_decision = self.memory_policy.decide(user_input, memory_context)
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
        log_event("route_decision", route.model_dump())
        
        plan_goal = user_input
        # If route decision is "Plan"
        plan_text = "No explicit plan created."
        
        if route.route == "plan":
            plan = self.planner.make_plan(user_input, memory_context)
            plan_goal = plan.goal
            log_event("plan_created", plan.model_dump())
            
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
                
        if replan_decision is not None and replan_decision.should_replan and len(replan_decision.next_steps) > 0:
            revised_steps = []
            for i, step in enumerate(replan_decision.next_steps, start=1):
                revised_steps.append(f"{i}. {step.step}")
            
            revised_plan_text = (
                f"Goal: {replan_decision.revised_goal}\n" + "\n".join(revised_steps)
            )
            
            log_event("revised_plan_created", {
                "goal": replan_decision.revised_goal,
                "steps": [s.step for s in replan_decision.next_steps]
            })
            
            second_answer, second_used_tools, second_tool_results = self._run_execution_cycle(
                route=route,
                memory_context=memory_context,
                plan_text=revised_plan_text,
                recent_history=self.memory.get_recent_history(),
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
            
        self.memory.add_history("assistant", final_answer)

        log_event("final_answer", {
            "text": final_answer,
            "used_tools": used_tools
        })

        return final_answer
        