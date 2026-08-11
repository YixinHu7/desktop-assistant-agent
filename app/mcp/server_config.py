import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


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

        configs.append(
            MCPServerConfig(
                name=str(item["name"]),
                command=str(item["command"]),
                args=[str(arg) for arg in item.get("args", [])],
                env={str(key): str(value) for key, value in item.get("env", {}).items()},
                enabled=bool(item.get("enabled", True)),
            )
        )

    return configs