import os
from dotenv import load_dotenv
from openai import OpenAI
from app.agent import DesktopAssistantAgent

def main():
    load_dotenv()
    
    agent = DesktopAssistantAgent()

    print("Desktop Assistant Agent is online. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Goodbye.")
            break

        result = agent.handle_user_message(user_input)
        print(f"Assistant: {result}")

if __name__ == "__main__":
    main()