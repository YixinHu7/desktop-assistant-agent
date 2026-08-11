from dataclasses import dataclass
from typing import Any, Literal, Protocol


RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    requires_approval: bool = True
    risk_level: RiskLevel = "high"
    permission_reason: str = "MCP tool requires approval by default."
    provider_name: str | None = None
    original_name: str | None = None


class MCPProvider(Protocol):
    provider_name: str

    def list_tool_specs(self) -> list[MCPToolSpec]:
        ...

    def call_tool(self, tool_name: str, arguments: dict[str, Any]):
        ...