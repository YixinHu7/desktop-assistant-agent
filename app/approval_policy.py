from pydantic import BaseModel
from typing import Literal


class ApprovalDecision(BaseModel):
    required: bool
    risk_level: Literal["low", "medium", "high"]
    reason: str


class ApprovalPolicy:
    def decide(self, tool_name: str, arguments: dict) -> ApprovalDecision:
        if tool_name == "open_app":
            return ApprovalDecision(
                required=True,
                risk_level="medium",
                reason="Opening desktop applications changes the user's local environment."
            )

        if tool_name == "create_note":
            return ApprovalDecision(
                required=False,
                risk_level="low",
                reason="Creating a note is low risk and reversible."
            )

        if tool_name == "save_memory_fact":
            return ApprovalDecision(
                required=False,
                risk_level="low",
                reason="Saving explicit user memory is allowed when requested."
            )

        if tool_name in {"read_file", "list_files"}:
            return ApprovalDecision(
                required=False,
                risk_level="low",
                reason="Reading local project files is allowed in this local assistant context."
            )

        return ApprovalDecision(
            required=True,
            risk_level="high",
            reason="Unknown tools require approval by default."
        )