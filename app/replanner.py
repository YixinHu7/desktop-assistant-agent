from openai import OpenAI
from app.schemas import ReplanDecision


class Replanner:
    def __init__(self, client: OpenAI):
        self.client = client

    def replan(
        self,
        user_input: str,
        original_goal: str,
        plan_text: str,
        tool_results_text: str,
        step_review_text: str,
        memory_context: str,
    ) -> ReplanDecision:
        prompt = f"""
You are a replanning module for a desktop assistant agent.

User request:
{user_input}

Original goal:
{original_goal}

Original plan:
{plan_text}

Tool results:
{tool_results_text}

Step review:
{step_review_text}

Memory context:
{memory_context}

Decide whether the agent should replan.

Rules:
- Only replan if meaningful progress is still possible with the currently available tools.
- If the remaining work cannot actually be completed with current tools, do not replan.
- If replanning, produce a short revised goal and a concise list of next executable steps.
- If not replanning, explain why clearly.
"""

        response = self.client.responses.parse(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": "Return a structured replanning decision."},
                {"role": "user", "content": prompt},
            ],
            text_format=ReplanDecision,
        )

        return response.output_parsed