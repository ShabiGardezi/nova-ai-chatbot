"""Centralized configuration loaded from environment variables.

All tunable settings live here so the rest of the app depends on a single,
validated ``Config`` object instead of reading ``os.environ`` directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_HISTORY_MESSAGES = 20
# Per-1k-token prices used for the cost estimate. Default 0.0 keeps the
# implementation provider agnostic (e.g. free Groq models report $0).
DEFAULT_PROMPT_COST_PER_1K = 0.0
DEFAULT_COMPLETION_COST_PER_1K = 0.0
DEFAULT_DATABASE_URL = "sqlite:///chatbot.db"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable application configuration."""

    api_key: str
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_history_messages: int = DEFAULT_MAX_HISTORY_MESSAGES
    base_url: str | None = None
    prompt_cost_per_1k: float = DEFAULT_PROMPT_COST_PER_1K
    completion_cost_per_1k: float = DEFAULT_COMPLETION_COST_PER_1K
    database_url: str = DEFAULT_DATABASE_URL

    @classmethod
    def load(cls) -> "Config":
        """Build a ``Config`` from the environment (and a local ``.env`` file).

        Raises:
            ConfigError: If ``OPENAI_API_KEY`` is missing or a numeric setting
                cannot be parsed.
        """
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )

        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

        # Optional: point the OpenAI-compatible client at another provider
        # (e.g. Groq, OpenRouter, Ollama). Empty means use OpenAI's default.
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None

        try:
            temperature = float(
                os.getenv("OPENAI_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            )
        except ValueError as exc:
            raise ConfigError("OPENAI_TEMPERATURE must be a number.") from exc

        try:
            max_history_messages = int(
                os.getenv("MAX_HISTORY_MESSAGES", str(DEFAULT_MAX_HISTORY_MESSAGES))
            )
        except ValueError as exc:
            raise ConfigError("MAX_HISTORY_MESSAGES must be an integer.") from exc

        if max_history_messages < 1:
            raise ConfigError("MAX_HISTORY_MESSAGES must be at least 1.")

        prompt_cost_per_1k = _get_float(
            "PROMPT_COST_PER_1K", DEFAULT_PROMPT_COST_PER_1K
        )
        completion_cost_per_1k = _get_float(
            "COMPLETION_COST_PER_1K", DEFAULT_COMPLETION_COST_PER_1K
        )

        database_url = (
            os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
            or DEFAULT_DATABASE_URL
        )

        return cls(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_history_messages=max_history_messages,
            base_url=base_url,
            prompt_cost_per_1k=prompt_cost_per_1k,
            completion_cost_per_1k=completion_cost_per_1k,
            database_url=database_url,
        )


def _get_float(name: str, default: float) -> float:
    """Read a non-negative float from the environment, with validation."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number.") from exc
    if value < 0:
        raise ConfigError(f"{name} must not be negative.")
    return value
