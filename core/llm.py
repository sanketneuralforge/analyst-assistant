# core/llm.py

import os
import time
import random
from groq import Groq, RateLimitError
from dotenv import load_dotenv
from core.logger import log_call
from core.model_router import get_model_for_mode, get_temperature_for_mode

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
    max_retries: int = 3,
) -> str:
    """
    Single entry point for all LLM calls.
    Now uses model router — each mode gets the right model automatically.
    Temperature is also routed unless explicitly overridden.
    """
    client = get_client()

    # Route to correct model and temperature
    model = get_model_for_mode(mode)
    temp = temperature if temperature is not None else get_temperature_for_mode(mode)

    for attempt in range(max_retries):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=model,
                temperature=temp,
                max_tokens=2048,
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
                model=model,
            )
            return output

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"  [rate limit] attempt {attempt+1}/{max_retries} — waiting {wait:.1f}s")
            time.sleep(wait)

    raise RuntimeError("LLM call failed after all retries")