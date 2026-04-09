import os
from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing in your .env file")

    client = OpenAI(api_key=api_key)

    print("Desktop Assistant Agent is online. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Goodbye.")
            break

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": "You are a concise desktop assistant."
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        )

        print(f"Assistant: {response.output_text}")


if __name__ == "__main__":
    main()