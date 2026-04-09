import os
from openai import OpenAI

from app.memory import MemoryStore
from app.router import Router
from app.logger import log_event

class DesktopAssistantAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing")
        
        self.client = OpenAI(api_key=api_key)
        self.memory = MemoryStore()
        self.router = Router(self.client)
        
        self.system_prompt = (
            "You are a concise desktop assistant. "
            "Be helpful, practical, and clear."
        )
    
    def handle_user_message(self, user_input: str) -> str:
        self.memory.add_history("user", user_input)
        
        memory_context = self.memory.get_context_text()
        route = self.router.decide(user_input, memory_context)
        log_event("route_decision", route.model_dump())
        
        final_prompt = f"""
Route selected: {route.route}
Reason: {route.reason}

Memory context:
{memory_context}

User input:
{user_input}
"""

        response = self.client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": final_prompt}
            ]
        )
        
        final_answer = response.output_text.strip() or "Done."
        self.memory.add_history("assistant", final_answer)
        log_event("final_answer", {"text": final_answer})
        
        return final_answer
        