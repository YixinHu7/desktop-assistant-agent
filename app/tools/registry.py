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
    }
]