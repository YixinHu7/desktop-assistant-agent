from openai import OpenAI
from app.schemas import ExecutionReview


class ExecutionReviewer:
    def __init__(self, client: OpenAI):
        self.client = client

    def review_execution(self, goal: str, plan_text: str, tool_results_text: str) -> ExecutionReview:
        prompt = f"""
You are an execution review module for a desktop assistant agent.

Your job is to review a plan against actual tool execution results.

Goal:
{goal}

Plan:
{plan_text}

Tool execution results:
{tool_results_text}

Rules:
- Mark a step as completed only if the available tool results support it.
- Mark a step as remaining if it still has not been done.
- Mark a step as skipped if it was effectively bypassed because another action already satisfied the user's goal.
- Mark a step as failed only if the step genuinely failed and was not successfully recovered.
- If an initial tool call failed but a recovery attempt succeeded and restored useful context or progress, reflect that in your judgment.
- Prefer judging overall task progress based on the latest successful evidence, not only the first failure.
"""

        response = self.client.responses.parse(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": "Return a structured execution review."},
                {"role": "user", "content": prompt},
            ],
            text_format=ExecutionReview,
        )

        return response.output_parsed