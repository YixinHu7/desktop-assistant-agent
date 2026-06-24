class ToolExecutor:
    def execute(self, tool_name: str, arguments: dict) -> dict:
        return {
            "ok": True,
            "tool": tool_name,
            "arguments": arguments,
        }