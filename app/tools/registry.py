TOOLS = [
    {
        "type": "function",
        "name": "create_note",
        "description": "Create a markdown note on disk.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["title", "content"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "open_app",
        "description": "Open a desktop application by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string"}
            },
            "required": ["app_name"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "list_files",
        "description": "List files in a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the content of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "save_memory_fact",
        "description": "Save important user information into long-term memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"}
            },
            "required": ["key", "value"],
            "additionalProperties": False
        },
        "strict": True
    }
]