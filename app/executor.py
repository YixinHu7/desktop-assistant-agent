from app.tools.system_tools import (
    create_note, 
    open_app,
    list_files,
    read_file,
    save_memory_fact
)

class ToolExecutor:
    def __init__(self, memory_store):
        self.memory_store = memory_store
        
    def execute(self, tool_name: str, arguments: dict):
        if tool_name == "create_note":
            return create_note(arguments["title"], arguments["content"])

        if tool_name == "open_app":
            return open_app(arguments["app_name"])
        
        if tool_name == "list_files":
            return list_files(arguments["path"])
        
        if tool_name == "read_file":
            return read_file(arguments["path"])
        
        if tool_name == "save_memory_fact":
            return save_memory_fact(self.memory_store, arguments["key"], arguments["value"])

        return {"ok": False, "error": f"Unknown tool: {tool_name}"}