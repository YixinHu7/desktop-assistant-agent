from app.mcp.mock_provider import MockMCPProvider

_provider = MockMCPProvider()


def mcp_search_docs(query: str, max_results: int = 5):
    return _provider.call_tool(
        "mcp_search_docs",
        {
            "query": query,
            "max_results": max_results,
        },
    )


def mcp_read_ticket(ticket_id: str):
    return _provider.call_tool(
        "mcp_read_ticket",
        {
            "ticket_id": ticket_id,
        },
    )


def mcp_list_resources(resource_type: str = "all"):
    return _provider.call_tool(
        "mcp_list_resources",
        {
            "resource_type": resource_type,
        },
    )