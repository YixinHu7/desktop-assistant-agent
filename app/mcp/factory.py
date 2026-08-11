from app.config import config
from app.mcp.mock_provider import MockMCPProvider
from app.mcp.provider import MCPProvider
from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import load_mcp_server_configs


def build_mcp_providers() -> list[MCPProvider]:
    if not config.enable_mcp_tools:
        return []

    providers: list[MCPProvider] = []

    if config.enable_mock_mcp_tools:
        providers.append(MockMCPProvider())

    if config.enable_real_mcp_tools:
        server_configs = load_mcp_server_configs(config.mcp_server_config_path)

        for server_config in server_configs:
            if server_config.enabled:
                providers.append(RealMCPProvider(server_config))

    return providers