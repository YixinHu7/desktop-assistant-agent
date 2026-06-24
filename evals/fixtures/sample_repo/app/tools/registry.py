from app.executor import ToolExecutor


def build_tool_registry() -> dict:
    return {"executor": ToolExecutor()}