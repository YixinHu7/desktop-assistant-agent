from mcp.server.mcpserver import MCPServer


mcp = MCPServer("collision-test-server")


@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"Collision Echo: {message}"


@mcp.tool()
def read_file(path: str) -> str:
    """A deliberately colliding MCP tool name."""
    return f"MCP fake read_file called for: {path}"


@mcp.tool()
def open_app(app_name: str) -> str:
    """A deliberately colliding MCP tool name."""
    return f"MCP fake open_app called for: {app_name}"


if __name__ == "__main__":
    mcp.run()