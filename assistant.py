"""
AI Assistant - A simple conversational AI assistant powered by OpenAI.

Usage:
    python assistant.py

Requirements:
    pip install openai
    Set OPENAI_API_KEY environment variable.
"""

import os
from openai import OpenAI

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer questions clearly and concisely."
)


def create_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it before running the assistant."
        )
    return OpenAI(api_key=api_key)


def chat(client: OpenAI, history: list[dict], user_message: str) -> str:
    history.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
    )
    assistant_message = response.choices[0].message.content or ""
    history.append({"role": "assistant", "content": assistant_message})
    return assistant_message


def main() -> None:
    print("AI Assistant is ready. Type 'quit' or 'exit' to stop.\n")
    try:
        client = create_client()
    except EnvironmentError as e:
        print(f"Error: {e}")
        return

    history: list[dict] = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye!")
            break

        try:
            response = chat(client, history, user_input)
        except Exception as e:  # noqa: BLE001
            print(f"Error communicating with the API: {e}\n")
            continue
        print(f"Assistant: {response}\n")


if __name__ == "__main__":
    main()
