# core/llm.py

import os
from groq import Groq
from dotenv import load_dotenv
from config.settings import settings

load_dotenv()

def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment")
    return Groq(api_key=api_key)


def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float | None = None,
) -> str:
    """
    Single entry point for all LLM calls in this project.
    Every mode goes through here — never call the client directly.
    This is where you'd add retry logic, cost tracking, and
    model routing in production.
    """
    client = get_client()
    temp = temperature if temperature is not None else settings.groq_temperature

    response = client.chat.completions.create(
        model=settings.groq_model,
        temperature=temp,
        max_tokens=settings.groq_max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content