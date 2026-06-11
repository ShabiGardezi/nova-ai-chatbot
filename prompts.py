"""System prompt definitions and helpers.

Besides the default prompt, this module defines selectable *personalities*
that the UI exposes. Each personality maps to a distinct system prompt so the
assistant's tone and focus change without any other code changes.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SYSTEM_PROMPT: str = (
    "You are a helpful, friendly AI assistant. "
    "Answer clearly and concisely. "
    "If you are unsure about something, say so instead of guessing."
)


@dataclass(frozen=True, slots=True)
class Personality:
    """A selectable assistant persona."""

    id: str
    name: str
    description: str
    prompt: str


PERSONALITIES: dict[str, Personality] = {
    "general": Personality(
        id="general",
        name="General Assistant",
        description="Friendly, well-rounded help for anything.",
        prompt=DEFAULT_SYSTEM_PROMPT,
    ),
    "architect": Personality(
        id="architect",
        name="Software Architect",
        description="System design, trade-offs, and clean architecture.",
        prompt=(
            "You are a senior software architect. Give pragmatic, opinionated "
            "guidance on system design, scalability, and trade-offs. Prefer "
            "clear reasoning, concrete examples, and call out risks and "
            "alternatives. Keep answers structured and concise."
        ),
    ),
    "interview": Personality(
        id="interview",
        name="Interview Coach",
        description="Mock interviews, feedback, and prep strategy.",
        prompt=(
            "You are an expert technical interview coach. Help the user prepare "
            "for software engineering interviews. Ask clarifying questions, give "
            "structured feedback, model strong answers, and explain the "
            "reasoning interviewers look for. Be encouraging but honest."
        ),
    ),
}

DEFAULT_PERSONALITY = "general"


def get_system_prompt(override: str | None = None) -> str:
    """Return the active system prompt.

    Args:
        override: Optional custom prompt. When provided and non-empty, it
            replaces the default.
    """
    if override and override.strip():
        return override.strip()
    return DEFAULT_SYSTEM_PROMPT


def get_personality_prompt(personality_id: str | None) -> str:
    """Return the system prompt for a personality id (falling back to default)."""
    personality = PERSONALITIES.get(
        (personality_id or "").strip(), PERSONALITIES[DEFAULT_PERSONALITY]
    )
    return personality.prompt


def list_personalities() -> list[dict[str, str]]:
    """Return personalities as serializable dicts for the API/UI."""
    return [
        {"id": p.id, "name": p.name, "description": p.description}
        for p in PERSONALITIES.values()
    ]
