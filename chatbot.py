"""Core chatbot service wrapping the OpenAI client and conversation memory."""

from __future__ import annotations

from collections.abc import Iterator

from openai import OpenAI

from config import Config
from memory import ConversationMemory, Message
from storage import ConversationStore
from usage import TokenUsage


class Chatbot:
    """Stateful chat service that remembers context across turns."""

    def __init__(
        self,
        config: Config,
        store: ConversationStore | None = None,
        conversation_id: int | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._config = config
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self._memory = ConversationMemory(
            max_history_messages=config.max_history_messages,
            system_prompt=system_prompt,
        )
        self.last_usage: TokenUsage | None = None
        self._store = store
        self._conversation_id = conversation_id
        if store is not None and conversation_id is not None:
            self._memory.load(store.get_messages(conversation_id))

    @property
    def conversation_id(self) -> int | None:
        """Id of the conversation currently being persisted, if any."""
        return self._conversation_id

    def send(self, user_input: str) -> str:
        """Send a user message and return the assistant's reply.

        Raises:
            openai.OpenAIError: If the API request fails.
        """
        self._memory.add_user(user_input)
        self._persist("user", user_input)
        self.last_usage = None

        response = self._client.chat.completions.create(
            model=self._config.model,
            temperature=self._config.temperature,
            messages=self._messages_payload(),
        )
        reply = response.choices[0].message.content or ""
        self.last_usage = TokenUsage.from_response(getattr(response, "usage", None))

        self._memory.add_assistant(reply)
        self._persist("assistant", reply)
        return reply

    def stream(self, user_input: str) -> Iterator[str]:
        """Stream the assistant's reply, yielding text chunks as they arrive.

        The fully assembled reply (or whatever was received before an error)
        is stored in memory once the stream ends, keeping context intact.

        Raises:
            openai.OpenAIError: If the API request fails. Any text received
                before the failure is still persisted to memory.
        """
        self._memory.add_user(user_input)
        self._persist("user", user_input)
        self.last_usage = None

        chunks: list[str] = []
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                temperature=self._config.temperature,
                messages=self._messages_payload(),
                stream=True,
                stream_options={"include_usage": True},
            )
            for event in response:
                event_usage = getattr(event, "usage", None)
                if event_usage is not None:
                    self.last_usage = TokenUsage.from_response(event_usage)
                if not event.choices:
                    continue
                delta = event.choices[0].delta.content
                if delta:
                    chunks.append(delta)
                    yield delta
        finally:
            if chunks:
                reply = "".join(chunks)
                self._memory.add_assistant(reply)
                self._persist("assistant", reply)

    def estimate_cost(self, usage: TokenUsage) -> float:
        """Approximate cost of a request using the configured per-1k prices."""
        return usage.cost(
            self._config.prompt_cost_per_1k,
            self._config.completion_cost_per_1k,
        )

    def clear(self) -> None:
        """Reset the in-memory context (the persisted log is left intact)."""
        self._memory.clear()

    def resume(self, conversation_id: int) -> int:
        """Load a stored conversation into memory and return its message count.

        Raises:
            RuntimeError: If persistence is disabled.
            KeyError: If the conversation does not exist.
        """
        if self._store is None:
            raise RuntimeError("Persistence is disabled.")
        messages = self._store.get_messages(conversation_id)
        self._memory.clear()
        self._memory.load(messages)
        self._conversation_id = conversation_id
        return len(messages)

    def start_new(self) -> None:
        """Drop the current context so the next message starts a new record."""
        self._memory.clear()
        self._conversation_id = None

    def _persist(self, role: str, content: str) -> None:
        if self._store is None:
            return
        if self._conversation_id is None:
            title = content.strip()[:60] if role == "user" else None
            self._conversation_id = self._store.create_conversation(title)
        self._store.add_message(self._conversation_id, role, content)

    def _messages_payload(self) -> list[Message]:
        return self._memory.get_messages()
