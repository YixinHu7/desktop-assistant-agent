class ToolExecutor:
    def __init__(self, tool_definitions):
        self.tool_definitions = tool_definitions
    
    def execute(self, tool_name: str, arguments: dict):
        tool = self.tool_definitions.get(tool_name)

        if tool is None:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}

        try:
            return tool.function(**arguments)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def requires_approval(self, tool_name: str) -> bool:
        tool = self.tool_definitions.get(tool_name)
        return tool.requires_approval if tool else False