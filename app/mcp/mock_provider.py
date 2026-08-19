from app.config import config
from app.mcp.provider import MCPProvider, MCPToolSpec
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


class MockMCPProvider(MCPProvider):
    provider_name = "mock_mcp"

    def list_tool_specs(self) -> list[MCPToolSpec]:
        return [
            MCPToolSpec(
                name="mcp_search_docs",
                description=(
                    "Search deterministic mock MCP documentation resources. "
                    "Use this when the user asks to search MCP docs, agent runtime docs, "
                    "evaluation docs, or MCP integration notes."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for mock MCP docs.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of documents to return.",
                        },
                    },
                    "required": ["query", "max_results"],
                    "additionalProperties": False,
                },
                requires_approval=False,
                risk_level="low",
                permission_reason="Read-only mock MCP documentation search.",
            ),
            MCPToolSpec(
                name="mcp_read_ticket",
                description=(
                    "Read a deterministic mock MCP ticket by ticket id. "
                    "Use this when the user asks about a ticket such as TICKET-123."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "Ticket id, for example TICKET-123.",
                        }
                    },
                    "required": ["ticket_id"],
                    "additionalProperties": False,
                },
                requires_approval=False,
                risk_level="low",
                permission_reason="Read-only mock MCP ticket lookup.",
            ),
            MCPToolSpec(
                name="mcp_list_resources",
                description=(
                    "List deterministic mock MCP resources. "
                    "Use this when the user asks what MCP docs or tickets are available."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "resource_type": {
                            "type": "string",
                            "enum": ["all", "docs", "tickets"],
                            "description": "Resource category to list.",
                        }
                    },
                    "required": ["resource_type"],
                    "additionalProperties": False,
                },
                requires_approval=False,
                risk_level="low",
                permission_reason="Read-only mock MCP resource listing.",
            ),
        ]

    def call_tool(self, tool_name: str, arguments: dict):
        if not self._enabled():
            return tool_error(
                message="Mock MCP tools are only available in evaluation mode.",
                metadata={
                    "tool": tool_name,
                    "provider": self.provider_name,
                    "original_tool": tool_name,
                    "exposed_tool": tool_name,
                    "mock_mcp_disabled": True,
                },
            )

        if tool_name == "mcp_search_docs":
            return self.search_docs(
                query=arguments["query"],
                max_results=arguments["max_results"],
            )

        if tool_name == "mcp_read_ticket":
            return self.read_ticket(ticket_id=arguments["ticket_id"])

        if tool_name == "mcp_list_resources":
            return self.list_resources(resource_type=arguments["resource_type"])

        return tool_error(
            message=f"Unknown mock MCP tool: {tool_name}",
            metadata={
                "tool": tool_name,
                "provider": self.provider_name,
                "original_tool": tool_name,
                "exposed_tool": tool_name,
            },
        )

    def search_docs(self, query: str, max_results: int = 5):
        normalized_query = query.lower()
        matches = []

        for doc in MOCK_DOCS:
            haystack = " ".join([doc["title"], doc["uri"], doc["content"]]).lower()

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
                "provider": self.provider_name,
                "original_tool": "mcp_search_docs",
                "exposed_tool": "mcp_search_docs",
                "eval_mode": config.eval_mode,
            },
        )

    def read_ticket(self, ticket_id: str):
        ticket = MOCK_TICKETS.get(ticket_id)

        if ticket is None:
            return tool_error(
                message=f"Ticket not found: {ticket_id}",
                metadata={
                    "tool": "mcp_read_ticket",
                    "provider": self.provider_name,
                    "ticket_id": ticket_id,
                },
            )

        return tool_success(
            data={"ticket": ticket},
            metadata={
                "tool": "mcp_read_ticket",
                "provider": self.provider_name,
                "original_tool": "mcp_read_ticket",
                "exposed_tool": "mcp_read_ticket",
                "ticket_id": ticket_id,
                "eval_mode": config.eval_mode,
            },
        )

    def list_resources(self, resource_type: str = "all"):
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
                "provider": self.provider_name,
                "original_tool": "mcp_list_resources",
                "exposed_tool": "mcp_list_resources",
                "eval_mode": config.eval_mode,
            },
        )

    def _enabled(self) -> bool:
        return config.eval_mode and config.enable_mock_mcp_tools