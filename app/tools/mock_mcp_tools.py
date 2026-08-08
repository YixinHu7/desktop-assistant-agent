from app.config import config
from app.tools.results import tool_error, tool_success


MOCK_DOCS = [
    {
        "id": "doc-agent-runtime",
        "title": "Agent Runtime Architecture",
        "uri": "mcp://docs/agent-runtime",
        "content": (
            "The desktop assistant runtime includes a router, planner, "
            "tool executor, reviewer, recovery manager, and memory store."
        ),
    },
    {
        "id": "doc-evaluation",
        "title": "Evaluation System",
        "uri": "mcp://docs/evaluation-system",
        "content": (
            "The evaluation system validates routing, skills, tool calls, "
            "approval behavior, recovery, completion, and answer grounding."
        ),
    },
    {
        "id": "doc-mcp",
        "title": "MCP Integration Plan",
        "uri": "mcp://docs/mcp-integration",
        "content": (
            "MCP tools should be discovered through a provider interface "
            "and executed through the same policy and telemetry path as "
            "local tools."
        ),
    },
]

MOCK_TICKETS = {
    "TICKET-123": {
        "ticket_id": "TICKET-123",
        "title": "Add MCP eval harness",
        "status": "in_progress",
        "priority": "medium",
        "summary": (
            "Create deterministic mock MCP tools before connecting a real "
            "MCP server."
        ),
    },
    "TICKET-456": {
        "ticket_id": "TICKET-456",
        "title": "Protect MCP side effects",
        "status": "blocked",
        "priority": "high",
        "summary": (
            "MCP tools that write, delete, send, or launch external actions "
            "must pass approval policy before execution."
        ),
    },
}


def _mock_mcp_enabled():
    return config.eval_mode and config.enable_mock_mcp_tools


def mcp_search_docs(query: str, max_results: int = 5):
    if not _mock_mcp_enabled():
        return tool_error(
            message="Mock MCP tools are only available in evaluation mode.",
            metadata={"tool": "mcp_search_docs", "mock_mcp_disabled": True},
        )

    normalized_query = query.lower()
    matches = []

    for doc in MOCK_DOCS:
        haystack = " ".join(
            [doc["title"], doc["uri"], doc["content"]]
        ).lower()

        if normalized_query in haystack or any(
            token in haystack for token in normalized_query.split()
        ):
            matches.append(doc)

    return tool_success(
        data={
            "query": query,
            "documents": matches[:max_results],
            "match_count": len(matches),
        },
        metadata={
            "tool": "mcp_search_docs",
            "provider": "mock_mcp",
            "eval_mode": config.eval_mode,
        },
    )


def mcp_read_ticket(ticket_id: str):
    if not _mock_mcp_enabled():
        return tool_error(
            message="Mock MCP tools are only available in evaluation mode.",
            metadata={"tool": "mcp_read_ticket", "mock_mcp_disabled": True},
        )

    ticket = MOCK_TICKETS.get(ticket_id)

    if ticket is None:
        return tool_error(
            message=f"Ticket not found: {ticket_id}",
            metadata={
                "tool": "mcp_read_ticket",
                "provider": "mock_mcp",
                "ticket_id": ticket_id,
            },
        )

    return tool_success(
        data={"ticket": ticket},
        metadata={
            "tool": "mcp_read_ticket",
            "provider": "mock_mcp",
            "ticket_id": ticket_id,
            "eval_mode": config.eval_mode,
        },
    )


def mcp_list_resources(resource_type: str = "all"):
    if not _mock_mcp_enabled():
        return tool_error(
            message="Mock MCP tools are only available in evaluation mode.",
            metadata={"tool": "mcp_list_resources", "mock_mcp_disabled": True},
        )

    resources = []

    if resource_type in {"all", "docs"}:
        resources.extend(
            {
                "type": "doc",
                "id": doc["id"],
                "title": doc["title"],
                "uri": doc["uri"],
            }
            for doc in MOCK_DOCS
        )

    if resource_type in {"all", "tickets"}:
        resources.extend(
            {
                "type": "ticket",
                "id": ticket["ticket_id"],
                "title": ticket["title"],
                "status": ticket["status"],
            }
            for ticket in MOCK_TICKETS.values()
        )

    return tool_success(
        data={
            "resource_type": resource_type,
            "resources": resources,
            "resource_count": len(resources),
        },
        metadata={
            "tool": "mcp_list_resources",
            "provider": "mock_mcp",
            "eval_mode": config.eval_mode,
        },
    )