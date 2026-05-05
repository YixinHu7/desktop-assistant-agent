from openai import OpenAI
from app.schemas import PlanOutput
from app.config import config


class Planner:
    def __init__(self, client: OpenAI):
        self.client = client
        
    def make_plan(self, user_input: str, memory_context: str) -> PlanOutput:
        prompt = f"""
You are a planning module for a desktop assistant agent.

Break the user's request into short, practical, executable steps.

Rules:
- Keep steps concrete
- Keep steps minimal
- Do not execute anything
- Only produce a plan

Memory context:
{memory_context}

User request:
{user_input}
"""
        response = self.client.responses.parse(
            model=config.model,
            input=[
                {"role": "system", "content": "Return a structured plan."},
                {"role": "user", "content": prompt},
            ],
            text_format=PlanOutput
        )
        
        return response.output_parsed