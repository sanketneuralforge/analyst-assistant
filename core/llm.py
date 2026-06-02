# core/llm.py

import os
import time
import random
from groq import Groq, RateLimitError
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
    max_retries: int = 3,
) -> str:
    client = get_client()
    temp = temperature if temperature is not None else settings.groq_temperature

    for attempt in range(max_retries):
        try:
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

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise  # re-raise on final attempt
            # Exponential backoff with jitter
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"  [rate limit] attempt {attempt+1}/{max_retries} — waiting {wait:.1f}s")
            time.sleep(wait)

    raise RuntimeError("LLM call failed after all retries")