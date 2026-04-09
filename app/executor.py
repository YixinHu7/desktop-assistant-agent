from app.tools.system_tools import create_note, open_app

class ToolExecutor:
    def execute(self, tool_name: str, arguments: dict):
        if tool_name == "create_note":
            return create_note(arguments["title"], arguments["content"])

        if tool_name == "open_app":
            return open_app(arguments["app_name"])

        return {"ok": False, "error": f"Unknown tool: {tool_name}"}