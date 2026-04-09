import json
import os
from openai import OpenAI

from app.memory import MemoryStore
from app.router import Router
from app.logger import log_event
from app.executor import ToolExecutor
from app.tools.registry import TOOLS

class DesktopAssistantAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing")
        
        self.client = OpenAI(api_key=api_key)
        self.memory = MemoryStore()
        self.router = Router(self.client)
        self.executor = ToolExecutor(self.memory)
        
        self.system_prompt = (
            "You are a concise desktop assistant agent. "
            "Be helpful, practical, and operationally clear. "
            "Use tools when they are genuinely useful. "
            "Do not invent tool results."
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
        route = self.router.decide(user_input, memory_context)
        log_event("route_decision", route.model_dump())
        
        input_items = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "system",
                "content": f"Memory context:\n{memory_context}"
            },
            {
                "role": "system",
                "content": f"Routing decision: {route.route}. Reason: {route.reason}"
            }
        ]
        
        for msg in self.memory.get_recent_history():
            input_items.append(msg)

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
                log_event("final_answer", {"text": final_answer})
                return final_answer
            
            tool_outputs = []
            
            for call in function_calls:
                arguments = json.loads(call.arguments) if call.arguments else {}
                
                if not self._ask_for_approval(call.name, arguments):
                    result = {"ok": False, "error": "User denied approval"}
                else:
                    result = self.executor.execute(call.name, arguments)
                    
                log_event("tool_call", {
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
        