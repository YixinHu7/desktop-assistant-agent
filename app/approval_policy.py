from pydantic import BaseModel
from typing import Literal
from app.config import config


class ApprovalDecision(BaseModel):
    required: bool
    risk_level: Literal["low", "medium", "high"]
    reason: str


class ApprovalPolicy:
    def decide(self, tool_name: str, arguments: dict) -> ApprovalDecision:
        permissions = config.tool_permissions()
        tool_policy = permissions.get(tool_name)

        if tool_policy is None:
            return ApprovalDecision(
                required=True,
                risk_level="high",
                reason="Unknown tools require approval by default."
            )

        return ApprovalDecision(
            required=tool_policy["requires_approval"],
            risk_level=tool_policy["risk_level"],
            reason=tool_policy["reason"],
        )