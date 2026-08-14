import json

from app.config import config
from app.mcp.factory import build_mcp_providers


def main() -> None:
    providers = build_mcp_providers()

    output = {
        "config": {
            "enable_mcp_tools": config.enable_mcp_tools,
            "enable_mock_mcp_tools": config.enable_mock_mcp_tools,
            "enable_real_mcp_tools": config.enable_real_mcp_tools,
            "mcp_server_config_path": config.mcp_server_config_path,
        },
        "provider_count": len(providers),
        "providers": [],
    }

    for provider in providers:
        specs = provider.list_tool_specs()
        diagnostics = (
            provider.discovery_diagnostics()
            if hasattr(provider, "discovery_diagnostics")
            else {
                "provider_name": provider.provider_name,
                "status": "unknown",
            }
        )

        output["providers"].append(
            {
                "provider_name": provider.provider_name,
                "tool_specs": [spec.name for spec in specs],
                "diagnostics": diagnostics,
            }
        )

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()