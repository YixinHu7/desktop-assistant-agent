import json
from typing import Any, Optional

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from app.config import config
from app.evaluation.models import EvalCase


class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_correctness: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    instruction_following: float = Field(ge=0.0, le=1.0)
    groundedness_quality: float = Field(ge=0.0, le=1.0)
    overall_quality: float = Field(ge=0.0, le=1.0)

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    reason: str


def build_judge_prompt(case: EvalCase, run_summary: dict[str, Any]) -> str:
    expected = case.expected.model_dump(mode="json")
    compact_summary = {
        "route_decision": run_summary.get("route_decision"),
        "skill_decision": run_summary.get("skill_decision"),
        "selected_skill": run_summary.get("selected_skill"),
        "tool_calls": run_summary.get("tool_calls", []),
        "recovery_events": run_summary.get("recovery_events", []),
        "final_answer": run_summary.get("final_answer", ""),
    }

    rubric = case.expected.judge.rubric or (
        "Judge whether the assistant satisfied the user's request, "
        "used available evidence appropriately, avoided unsupported claims, "
        "and produced a useful final answer."
    )

    return f"""
You are an evaluation judge for a desktop assistant agent.

Evaluate the final answer and runtime behavior against the case expectations.

User input:
{case.input}

Case description:
{case.description}

Expected outcome:
{json.dumps(expected, ensure_ascii=False, indent=2)}

Runtime summary:
{json.dumps(compact_summary, ensure_ascii=False, indent=2)}

Rubric:
{rubric}

Scoring guide:
- semantic_correctness: Does the answer make correct claims?
- completeness: Does it answer the requested task fully?
- instruction_following: Did it follow the user request and eval expectations?
- groundedness_quality: Are claims supported by tool results or available evidence?
- overall_quality: Overall usefulness and reliability.

Return a structured judge score.
""".strip()


def run_llm_judge(
    client: OpenAI,
    case: EvalCase,
    run_summary: dict[str, Any],
    model: Optional[str] = None,
) -> JudgeScore:
    response = client.responses.parse(
        model=model or config.judge_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a strict but fair evaluator. "
                    "Return only the structured evaluation."
                ),
            },
            {
                "role": "user",
                "content": build_judge_prompt(case, run_summary),
            },
        ],
        text_format=JudgeScore,
    )

    return response.output_parsed