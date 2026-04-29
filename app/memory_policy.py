from pydantic import BaseModel
from typing import Literal, Optional
from openai import OpenAI


class MemoryDecision(BaseModel):
    action: Literal["none", "read", "write"]
    key: Optional[str] = None
    value: Optional[str] = None
    reason: str


class MemoryPolicy:
    def __init__(self, client: OpenAI):
        self.client = client

    def decide(self, user_input: str, memory_context: str) -> MemoryDecision:
        prompt = f"""
You are a memory policy module for a desktop assistant agent.

Decide whether the user's message requires memory action.

Actions:
- none: no memory action needed
- read: user is asking about something likely stored in memory
- write: user explicitly provides durable information to remember

Durable information examples:
- name
- preferences
- long-term interests
- recurring projects
- study/work context

Do NOT write temporary moods, one-time tasks, or random short-lived details.

Memory context:
{memory_context}

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": "Return a memory decision."},
                {"role": "user", "content": prompt},
            ],
            text_format=MemoryDecision,
        )

        return response.output_parsed