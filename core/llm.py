# core/llm.py

import os
import time
from groq import Groq
from dotenv import load_dotenv
from config.settings import settings
from core.logger import log_call

load_dotenv()


def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment")
    return Groq(api_key=api_key)


def call_llm(
    system_prompt: str,
    user_message: str,
    mode: str = "unknown",
    prompt_version: str = "unknown",
    temperature: float | None = None,
) -> str:
    """
    Single entry point for all LLM calls.
    Now times every call and logs to SQLite automatically.
    """
    client = get_client()
    temp = temperature if temperature is not None else settings.groq_temperature

    start = time.time()
    response = client.chat.completions.create(
        model=settings.groq_model,
        temperature=temp,
        max_tokens=settings.groq_max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    latency_ms = int((time.time() - start) * 1000)

    output = response.choices[0].message.content

    log_call(
        mode=mode,
        prompt_version=prompt_version,
        user_input=user_message,
        full_output=output,
        latency_ms=latency_ms,
        model=settings.groq_model,
    )

    return output