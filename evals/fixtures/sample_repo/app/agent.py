from app.executor import ToolExecutor
from app.planner import Planner
from app.router import Router


class DesktopAssistantAgent:
    def __init__(self) -> None:
        self.router = Router()
        self.planner = Planner()
        self.executor = ToolExecutor()

    def handle_user_message(self, user_input: str) -> str:
        route = self.router.decide(user_input)
        return f"Selected route: {route}"