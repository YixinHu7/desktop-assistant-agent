from app.tools.base import ToolDefinition
from app.tools.system_tools import (
    create_note,
    open_app,
    list_files,
    read_file,
    save_memory_fact,
    get_project_tree,
    find_file,
    search_files,
    read_multiple_files,
)
from app.config import config
from app.tools.mock_mcp_tools import (
    mcp_list_resources,
    mcp_read_ticket,
    mcp_search_docs,
)


def build_tool_definitions(memory_store):
    tools = {}
    permissions = config.tool_permissions()
    
    if permissions["list_files"]["enabled"]:
        tools["list_files"] = ToolDefinition(
            name="list_files",
            schema={
                "type": "function",
                "name": "list_files",
                "description": "List files in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            function=list_files,
            requires_approval=False,
            source="local",
        )
    
    if permissions["read_file"]["enabled"]:
        tools["read_file"] = ToolDefinition(
            name="read_file",
            schema={
                "type": "function",
                "name": "read_file",
                "description": "Read the content of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            function=read_file,
            requires_approval=False,
            source="local",
        )
    
    if permissions["get_project_tree"]["enabled"]:
        tools["get_project_tree"] = ToolDefinition(
            name="get_project_tree",
            schema={
                "type": "function",
                "name": "get_project_tree",
                "description": "Return a text tree of a project directory up to a maximum depth.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_depth": {"type": "integer"}
                    },
                    "required": ["path", "max_depth"],
                    "additionalProperties": False
                },
                "strict": True,
            },
            function=get_project_tree,
            requires_approval=permissions["list_files"]["requires_approval"],
            risk_level=permissions["list_files"]["risk_level"],
            permission_reason=permissions["list_files"]["reason"],
            source="local",
        )
    
    if permissions["find_file"]["enabled"]:
        tools["find_file"] = ToolDefinition(
            name="find_file",
            schema={
                "type": "function",
                "name": "find_file",
                "description": "Find files by partial filename match within a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "path": {"type": "string"}
                    },
                    "required": ["filename", "path"],
                    "additionalProperties": False
                },
                "strict": True,
            },
            function=find_file,
            requires_approval=permissions["list_files"]["requires_approval"],
            risk_level=permissions["list_files"]["risk_level"],
            permission_reason=permissions["list_files"]["reason"],
            source="local",
        )
    
    if permissions["search_files"]["enabled"]:
        tools["search_files"] = ToolDefinition(
            name="search_files",
            schema={
                "type": "function",
                "name": "search_files",
                "description": "Search text content across project files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "path": {"type": "string"},
                        "max_results": {"type": "integer"}
                    },
                    "required": ["query", "path", "max_results"],
                    "additionalProperties": False
                },
                "strict": True,
            },
            function=search_files,
            requires_approval=permissions["read_file"]["requires_approval"],
            risk_level=permissions["read_file"]["risk_level"],
            permission_reason=permissions["read_file"]["reason"],
            source="local",
        )
    
    if permissions["read_multiple_files"]["enabled"]:
        tools["read_multiple_files"] = ToolDefinition(
            name="read_multiple_files",
            schema={
                "type": "function",
                "name": "read_multiple_files",
                "description": "Read multiple local files at once.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["paths"],
                    "additionalProperties": False
                },
                "strict": True,
            },
            function=read_multiple_files,
            requires_approval=permissions["read_file"]["requires_approval"],
            risk_level=permissions["read_file"]["risk_level"],
            permission_reason=permissions["read_file"]["reason"],
            source="local",
        )
    
    if permissions["create_note"]["enabled"]:
        tools["create_note"] = ToolDefinition(
            name="create_note",
            schema={
                "type": "function",
                "name": "create_note",
                "description": "Create a markdown note on disk.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["title", "content"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            function=create_note,
            requires_approval=False,
            source="local",
        )
    
    if permissions["save_memory_fact"]["enabled"]:
        tools["save_memory_fact"] = ToolDefinition(
            name="save_memory_fact",
            schema={
                "type": "function",
                "name": "save_memory_fact",
                "description": "Save important user information into long-term memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            function=lambda key, value: save_memory_fact(memory_store, key, value),
            requires_approval=False,
            source="local",
        )
    
    if permissions["open_app"]["enabled"]:
        tools["open_app"] = ToolDefinition(
            name="open_app",
            schema={
                "type": "function",
                "name": "open_app",
                "description": "Open a desktop application by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string"},
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            function=open_app,
            requires_approval=True,
            source="local",
        )
    
    if config.enable_mcp_tools and config.enable_mock_mcp_tools:
        tools["mcp_search_docs"] = ToolDefinition(
            name="mcp_search_docs",
            schema={
                "type": "function",
                "name": "mcp_search_docs",
                "description": (
                    "Search deterministic mock MCP documentation resources. "
                    "Use this when the user asks to search MCP docs, agent runtime docs, "
                    "evaluation docs, or MCP integration notes."
                ),
                "parameters": {
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
                "strict": True,
            },
            function=mcp_search_docs,
            requires_approval=False,
            source="mock_mcp",
        )

        tools["mcp_read_ticket"] = ToolDefinition(
            name="mcp_read_ticket",
            schema={
                "type": "function",
                "name": "mcp_read_ticket",
                "description": (
                    "Read a deterministic mock MCP ticket by ticket id. "
                    "Use this when the user asks about a ticket such as TICKET-123."
                ),
                "parameters": {
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
                "strict": True,
            },
            function=mcp_read_ticket,
            requires_approval=False,
            source="mock_mcp",
        )

        tools["mcp_list_resources"] = ToolDefinition(
            name="mcp_list_resources",
            schema={
                "type": "function",
                "name": "mcp_list_resources",
                "description": (
                    "List deterministic mock MCP resources. "
                    "Use this when the user asks what MCP docs or tickets are available."
                ),
                "parameters": {
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
                "strict": True,
            },
            function=mcp_list_resources,
            requires_approval=False,
            source="mock_mcp",
        )
        
    return tools
    
def get_tool_schemas(tool_definitions):
    return [tool.schema for tool in tool_definitions.values()]