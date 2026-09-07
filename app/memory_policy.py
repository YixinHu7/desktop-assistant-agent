from typing import Literal, Optional

from openai import OpenAI
from pydantic import BaseModel

from app.config import config


class MemoryDecision(BaseModel):
    action: Literal["none", "read", "write"]
    key: Optional[str] = None
    value: Optional[str] = None
    reason: str


class MemoryPolicy:
    def __init__(self, client: OpenAI):
        self.client = client

    def decide(
        self,
        user_input: str,
        memory_context: str,
    ) -> MemoryDecision:
        prompt = f"""
You are a conservative memory policy module for a desktop assistant agent.

Decide whether the user's message requires a memory action.

Actions:
- none: no memory action is needed
- read: the user asks about something that may already be stored in memory
- write: the user explicitly asks the assistant to remember durable information

Only choose write when the user clearly wants durable information remembered.

Good write examples:
- "Remember that the default project branch is main."
- "Please remember that this project uses Python 3.12."
- "Going forward, use concise technical explanations."
- "From now on, prefer small incremental patches."

Do NOT write:
- temporary moods
- one-time tasks
- random short-lived facts
- ordinary questions
- inferred personal details
- sensitive personal attributes

When action is write:
- key must be a short snake_case string
- value must be the exact durable information to remember
- reason must explain why this is durable and explicitly requested

Memory context:
{memory_context}

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model=config.model,
            input=[
                {
                    "role": "system",
                    "content": "Return a memory decision.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=MemoryDecision,
        )

        return sanitize_memory_decision(
            decision=response.output_parsed,
            user_input=user_input,
        )


def sanitize_memory_decision(
    decision: MemoryDecision,
    user_input: str,
) -> MemoryDecision:
    if decision.action != "write":
        return decision

    key = _normalize_memory_key(decision.key)
    value = str(decision.value).strip() if decision.value is not None else ""

    if not key or not value:
        return MemoryDecision(
            action="none",
            key=None,
            value=None,
            reason=(
                "Memory write was rejected because the decision did not "
                "include both a non-empty key and value."
            ),
        )

    if not _has_explicit_memory_write_intent(user_input):
        return MemoryDecision(
            action="none",
            key=None,
            value=None,
            reason=(
                "Memory write was rejected because the user did not clearly "
                "ask to remember durable information."
            ),
        )

    return MemoryDecision(
        action="write",
        key=key,
        value=value,
        reason=decision.reason,
    )


def _normalize_memory_key(key: str | None) -> str:
    if key is None:
        return ""

    normalized = str(key).strip().lower()
    normalized = normalized.replace("-", "_").replace(" ", "_")
    normalized = "".join(char for char in normalized if char.isalnum() or char == "_")

    while "__" in normalized:
        normalized = normalized.replace("__", "_")

    return normalized.strip("_")


def _has_explicit_memory_write_intent(user_input: str) -> bool:
    text = user_input.lower()

    write_markers = [
        "remember",
        "remember that",
        "please remember",
        "save this",
        "save that",
        "store this",
        "store that",
        "note that",
        "keep in mind",
        "from now on",
        "going forward",
        "use this preference",
        "default to",
        "prefer",
    ]

    return any(marker in text for marker in write_markers)
