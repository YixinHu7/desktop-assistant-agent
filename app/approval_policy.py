from typing import Any, Literal, Mapping

from pydantic import BaseModel

from app.config import config


class ApprovalDecision(BaseModel):
    required: bool
    risk_level: Literal["low", "medium", "high"]
    reason: str


class ApprovalPolicy:
    def __init__(self, tool_definitions: Mapping[str, Any] | None = None):
        self._tool_definitions = tool_definitions or {}

    def decide(self, tool_name: str, arguments: dict) -> ApprovalDecision:
        permissions = config.tool_permissions()
        tool_policy = permissions.get(tool_name)

        if tool_policy is not None:
            return ApprovalDecision(
                required=tool_policy["requires_approval"],
                risk_level=tool_policy["risk_level"],
                reason=tool_policy["reason"],
            )

        tool_definition = self._tool_definitions.get(tool_name)

        if tool_definition is not None:
            return ApprovalDecision(
                required=bool(getattr(tool_definition, "requires_approval", True)),
                risk_level=getattr(tool_definition, "risk_level", "high"),
                reason=getattr(
                    tool_definition,
                    "permission_reason",
                    "Tool requires approval by registry policy.",
                ),
            )

        return ApprovalDecision(
            required=True,
            risk_level="high",
            reason="Unknown tools require approval by default.",
        )