# config/settings.py

from dataclasses import dataclass

@dataclass
class Settings:
    # ONE LINE CHANGE to switch providers
    llm_provider: str = "groq"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.3      # low = more deterministic, good for analysis
    groq_max_tokens: int = 2048

settings = Settings()