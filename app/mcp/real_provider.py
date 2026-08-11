from app.mcp.provider import MCPProvider, MCPToolSpec
from app.mcp.server_config import MCPServerConfig
from app.tools.results import tool_error


class RealMCPProvider(MCPProvider):
    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.provider_name = f"mcp:{server_config.name}"

    def list_tool_specs(self) -> list[MCPToolSpec]:
        
        return []

    def call_tool(self, tool_name: str, arguments: dict):
        return tool_error(
            message=(
                "Real MCP tool execution is not implemented yet. "
                "Use mock MCP tools for evaluation."
            ),
            metadata={
                "tool": tool_name,
                "provider": self.provider_name,
                "server": self.server_config.name,
                "real_mcp_not_implemented": True,
            },
        )