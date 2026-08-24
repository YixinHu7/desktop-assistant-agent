import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

RiskLevel = Literal["low", "medium", "high"]
VALID_RISK_LEVELS = {"low", "medium", "high"}


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
    servers = _extract_servers(raw)

    return [_parse_server_config(item) for item in servers]


def _extract_servers(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        servers = raw.get("servers", [])
    elif isinstance(raw, list):
        servers = raw
    else:
        raise ValueError(
            "MCP server config must be a list or an object with 'servers'."
        )

    if not isinstance(servers, list):
        raise ValueError("MCP server config field 'servers' must be a list.")

    for item in servers:
        if not isinstance(item, dict):
            raise ValueError("Each MCP server config must be an object.")

    return servers


def _parse_server_config(item: dict[str, Any]) -> MCPServerConfig:
    name = _required_non_empty_string(item, "name")
    command = _required_non_empty_string(item, "command")

    args = _string_list(item.get("args", []), "args")
    env = _string_dict(item.get("env", {}), "env")
    enabled = _bool_value(item.get("enabled", True), "enabled")
    allowed_tools = _unique_string_list(item.get("allowed_tools", []), "allowed_tools")
    tool_policies = _parse_tool_policies(
        raw=item.get("tool_policies", {}),
        allowed_tools=allowed_tools,
    )

    return MCPServerConfig(
        name=name,
        command=command,
        args=args,
        env=env,
        enabled=enabled,
        allowed_tools=allowed_tools,
        tool_policies=tool_policies,
        list_timeout_seconds=_positive_float(
            item.get("list_timeout_seconds", 5.0),
            "list_timeout_seconds",
        ),
        call_timeout_seconds=_positive_float(
            item.get("call_timeout_seconds", 10.0),
            "call_timeout_seconds",
        ),
    )


def _parse_tool_policies(
    raw: Any,
    allowed_tools: list[str],
) -> dict[str, MCPToolPolicy]:
    if raw is None:
        return {}

    if not isinstance(raw, dict):
        raise ValueError("MCP server config field 'tool_policies' must be an object.")

    allowed_tool_set = set(allowed_tools)
    policies = {}

    for tool_name, policy in raw.items():
        tool = str(tool_name).strip()

        if not tool:
            raise ValueError("MCP tool policy names cannot be empty.")

        if tool not in allowed_tool_set:
            raise ValueError(
                "MCP tool policy was configured for a tool that is not allowed: "
                f"{tool}."
            )

        if not isinstance(policy, dict):
            raise ValueError(f"MCP tool policy for '{tool}' must be an object.")

        policies[tool] = MCPToolPolicy(
            requires_approval=_bool_value(
                policy.get("requires_approval", True),
                f"tool_policies.{tool}.requires_approval",
            ),
            risk_level=_risk_level(
                policy.get("risk_level", "high"),
                f"tool_policies.{tool}.risk_level",
            ),
            reason=_optional_non_empty_string(
                policy.get(
                    "reason",
                    "Real MCP tool requires approval by default.",
                ),
                f"tool_policies.{tool}.reason",
            ),
        )

    return policies


def _required_non_empty_string(
    item: dict[str, Any],
    field_name: str,
) -> str:
    if field_name not in item:
        raise ValueError(f"MCP server config requires field '{field_name}'.")

    return _optional_non_empty_string(item[field_name], field_name)


def _optional_non_empty_string(
    value: Any,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"MCP server config field '{field_name}' must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"MCP server config field '{field_name}' cannot be empty.")

    return normalized


def _string_list(
    value: Any,
    field_name: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"MCP server config field '{field_name}' must be a list.")

    return [str(item) for item in value]


def _unique_string_list(
    value: Any,
    field_name: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"MCP server config field '{field_name}' must be a list.")

    normalized = []

    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"MCP server config field '{field_name}' must contain only strings."
            )

        name = item.strip()

        if not name:
            raise ValueError(
                f"MCP server config field '{field_name}' cannot contain empty strings."
            )

        if name not in normalized:
            normalized.append(name)

    return normalized


def _string_dict(
    value: Any,
    field_name: str,
) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"MCP server config field '{field_name}' must be an object.")

    return {str(key): str(child) for key, child in value.items()}


def _bool_value(
    value: Any,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"MCP server config field '{field_name}' must be a boolean.")

    return value


def _positive_float(
    value: Any,
    field_name: str,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"MCP server config field '{field_name}' must be a positive number."
        ) from exc

    if number <= 0:
        raise ValueError(
            f"MCP server config field '{field_name}' must be greater than 0."
        )

    return number


def _risk_level(
    value: Any,
    field_name: str,
) -> RiskLevel:
    if not isinstance(value, str):
        raise ValueError(f"MCP server config field '{field_name}' must be a string.")

    normalized = value.strip().lower()

    if normalized not in VALID_RISK_LEVELS:
        raise ValueError(
            f"MCP server config field '{field_name}' must be one of "
            f"{sorted(VALID_RISK_LEVELS)}."
        )

    return cast(RiskLevel, normalized)
