import json
import os
from openai import OpenAI

from app.memory import MemoryStore
from app.router import Router
from app.logger import log_event
from app.executor import ToolExecutor
from app.tools.registry import TOOLS
from app.planner import Planner

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
        
        self.system_prompt = (
            "You are a concise desktop assistant agent. "
            "Be helpful, practical, and operationally clear. "
            "Use tools when they are genuinely useful. "
            "Do not invent tool results."
            "When a plan is provided, use it to guide execution step by step. "
            "Only mark progress that is supported by available evidence."
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
        
        # If route decision is "Plan"
        plan_text = "No explicit plan created."
        if route.route == "plan":
            plan = self.planner.make_plan(user_input, memory_context)
            log_event("plan_created", plan.model_dump())
            
            formatted_steps = []
            for i, step in enumerate(plan.steps, start=1):
                formatted_steps.append(f"{i}. {step.step}")
            
            plan_text = f"Goal: {plan.goal}\n" + "\n".join(formatted_steps)
        
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
        
        for msg in self.memory.get_recent_history():
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
            
            if not function_calls:
                final_answer = response.output_text.strip() or "Done."
                self.memory.add_history("assistant", final_answer)
                
                log_event("execution_summary", {
                    "route": route.route,
                    "plan": plan_text,
                    "used_tools": used_tools,
                    "tool_results_count": len(tool_results_for_summary),
                })
                
                log_event("final_answer", {
                    "text": final_answer,
                    "used_tools": used_tools
                })
                
                return final_answer
            
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
        