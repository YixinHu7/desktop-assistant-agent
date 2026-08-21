import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class MCPToolPolicy:
    requires_approval: bool = True
    risk_level: RiskLevel = "high"
    reason: str = "Real MCP tool requires approval by default."


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    allowed_tools: list[str] = field(default_factory=list)
    tool_policies: dict[str, MCPToolPolicy] = field(default_factory=dict)
    list_timeout_seconds: float = 5.0
    call_timeout_seconds: float = 10.0


def load_mcp_server_configs(path: str | Path) -> list[MCPServerConfig]:
    config_path = Path(path)

    if not config_path.exists():
        return []

    raw = json.loads(config_path.read_text(encoding="utf-8"))

    if isinstance(raw, dict):
        servers = raw.get("servers", [])
    elif isinstance(raw, list):
        servers = raw
    else:
        raise ValueError("MCP server config must be a list or an object with 'servers'.")

    configs = []

    for item in servers:
        if not isinstance(item, dict):
            raise ValueError("Each MCP server config must be an object.")

        tool_policies = {
            str(tool_name): MCPToolPolicy(
                requires_approval=bool(policy.get("requires_approval", True)),
                risk_level=policy.get("risk_level", "high"),
                reason=str(
                    policy.get(
                        "reason",
                        "Real MCP tool requires approval by default.",
                    )
                ),
            )
            for tool_name, policy in item.get("tool_policies", {}).items()
        }

        configs.append(
            MCPServerConfig(
                name=str(item["name"]),
                command=str(item["command"]),
                args=[str(arg) for arg in item.get("args", [])],
                env={str(key): str(value) for key, value in item.get("env", {}).items()},
                enabled=bool(item.get("enabled", True)),
                allowed_tools=[str(name) for name in item.get("allowed_tools", [])],
                tool_policies=tool_policies,
                list_timeout_seconds=float(item.get("list_timeout_seconds", 5.0)),
                call_timeout_seconds=float(item.get("call_timeout_seconds", 10.0)),
            )
        )

    return configs