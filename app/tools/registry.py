from app.tools.base import ToolDefinition
from app.tools.system_tools import (
    create_note,
    open_app,
    list_files,
    read_file,
    save_memory_fact,
)
from app.config import config


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
        
    return tools
    
def get_tool_schemas(tool_definitions):
    return [tool.schema for tool in tool_definitions.values()]