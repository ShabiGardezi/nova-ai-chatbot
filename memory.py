"""Conversation memory management.

Stores the running chat history and always exposes it prefixed with the
system prompt. Older turns are trimmed once the history exceeds the
configured cap so request payloads stay bounded.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypedDict, cast

from prompts import get_system_prompt

Role = Literal["system", "user", "assistant"]


class Message(TypedDict):
    """A single chat message in OpenAI's expected shape."""

    role: Role
    content: str


class ConversationMemory:
    """Holds the system prompt plus a trimmed window of recent messages."""

    def __init__(
        self,
        max_history_messages: int = 20,
        system_prompt: str | None = None,
    ) -> None:
        self._max_history_messages = max(1, max_history_messages)
        self._system: Message = {
            "role": "system",
            "content": get_system_prompt(system_prompt),
        }
        self._history: list[Message] = []

    def add_user(self, content: str) -> None:
        self._append("user", content)

    def add_assistant(self, content: str) -> None:
        self._append("assistant", content)

    def get_messages(self) -> list[Message]:
        """Return the system prompt followed by the retained history."""
        return [self._system, *self._history]

    def load(self, messages: Iterable[tuple[str, str]]) -> None:
        """Replace history with stored ``(role, content)`` pairs, then trim.

        Non user/assistant roles (e.g. a persisted system row) are ignored
        since the system prompt is always supplied separately.
        """
        self._history = [
            {"role": cast(Role, role), "content": content}
            for role, content in messages
            if role in ("user", "assistant")
        ]
        self._trim()

    def clear(self) -> None:
        """Drop all conversation history (the system prompt is preserved)."""
        self._history.clear()

    def _append(self, role: Role, content: str) -> None:
        self._history.append({"role": role, "content": content})
        self._trim()

    def _trim(self) -> None:
        if len(self._history) > self._max_history_messages:
            self._history = self._history[-self._max_history_messages :]
