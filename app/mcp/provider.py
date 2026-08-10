from dataclasses import dataclass
from typing import Protocol, Literal


RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    parameters: dict
    requires_approval: bool = False
    risk_level: RiskLevel = "low"
    permission_reason: str = "MCP tool permission."


class MCPProvider(Protocol):
    provider_name: str

    def list_tool_specs(self) -> list[MCPToolSpec]:
        ...

    def call_tool(self, tool_name: str, arguments: dict):
        ...