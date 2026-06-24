class Router:
    def decide(self, user_input: str) -> str:
        if "file" in user_input.lower():
            return "tool"

        return "chat"