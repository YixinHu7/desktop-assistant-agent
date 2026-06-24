from app.agent import DesktopAssistantAgent


def main() -> None:
    agent = DesktopAssistantAgent()
    print(agent.handle_user_message("Hello"))


if __name__ == "__main__":
    main()