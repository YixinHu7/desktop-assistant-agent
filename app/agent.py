import json
import os
from openai import OpenAI

from app.memory import MemoryStore
from app.router import Router
from app.logger import log_event
from app.executor import ToolExecutor
from app.tools.registry import TOOLS
from app.planner import Planner
from app.reviewer import ExecutionReviewer
from app.replanner import Replanner

class DesktopAssistantAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing")
        
        self.client = OpenAI(api_key=api_key)
        self.memory = MemoryStore()
        self.router = Router(self.client)
        self.executor = ToolExecutor(self.memory)
        self.planner = Planner(self.client)
        self.reviewer = ExecutionReviewer(self.client)
        self.replanner = Replanner(self.client)
        
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
            tools=TOOLS,
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
                    "result": result
                })
                
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False)
                })
            
            response = self.client.responses.create(
                model="gpt-4.1-mini",
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOLS,
                parallel_tool_calls=False
            )     
    
    def _ask_for_approval(self, tool_name: str, arguments: dict) -> bool:
        high_risk_tools = {"open_app"}
        if tool_name not in high_risk_tools:
            return True
        print(f"\n[Approval Required] {tool_name} with args={arguments}")
        answer = input("Approve? (y/n): ").strip().lower()
        return answer == "y"
    
    def handle_user_message(self, user_input: str) -> str:
        self.memory.add_history("user", user_input)
        
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
            
        log_event("execution_summary", {
            "route": route.route,
            "plan": plan_text,
            "used_tools": used_tools,
            "tool_results_count": len(tool_results_for_summary),
            "has_step_review": execution_review is not None,
            "has_replan_decision": replan_decision is not None,
            "replan_triggered": replan_decision.should_replan if replan_decision else False,
            "revised_plan_used": replan_decision.revised_goal if replan_decision and replan_decision.should_replan else None
        })
            
        self.memory.add_history("assistant", final_answer)

        log_event("final_answer", {
            "text": final_answer,
            "used_tools": used_tools
        })

        return final_answer
        