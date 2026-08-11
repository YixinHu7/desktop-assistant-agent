from mcp.server.mcpserver import MCPServer


mcp = MCPServer("tiny-test-server")


@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"Echo: {message}"


@mcp.tool()
def get_status() -> dict:
    """Return a deterministic test status."""
    return {
        "status": "ok",
        "service": "tiny-test-server",
    }


if __name__ == "__main__":
    mcp.run()