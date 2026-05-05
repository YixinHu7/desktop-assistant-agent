from openai import OpenAI
from app.schemas import RouteDecision
from app.config import config


class Router:
    def __init__(self, client: OpenAI):
        self.client = client

    def decide(self, user_input: str, memory_context: str) -> RouteDecision:
        prompt = f"""
You are a routing module for a desktop assistant agent.

Classify the user's request into exactly one route:
- chat: simple response, no tool use needed
- tool: likely solvable with one or two tool calls
- plan: complex or multi-step task that should be decomposed first

Memory context:
{memory_context}

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model=config.model,
            input=[
                {"role": "system", "content": "Return a routing decision."},
                {"role": "user", "content": prompt}
            ],
            text_format=RouteDecision
        )
        
        return response.output_parsed