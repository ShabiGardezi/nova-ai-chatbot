"""FastAPI backend for the AI chatbot web interface.

Reuses the existing service layer (``Config``, ``Chatbot``,
``ConversationStore``, prompts) and exposes a small JSON/SSE API plus the
static frontend in ``frontend/``.

Run with:
    uvicorn server:app --reload
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chatbot import Chatbot
from config import Config, ConfigError
from prompts import DEFAULT_PERSONALITY, get_personality_prompt, list_personalities
from storage import ConversationStore

FRONTEND_DIR = Path(__file__).parent / "frontend"

app = FastAPI(title="AI Chatbot")

# Built once at startup and shared across requests. A fresh ``Chatbot`` is
# created per chat turn (cheap) so each request can target its own
# conversation while the store/config stay shared.
try:
    settings: Config = Config.load()
except ConfigError as exc:  # pragma: no cover - surfaced at boot
    raise RuntimeError(f"Configuration error: {exc}") from exc

store = ConversationStore(settings.database_url)


class ChatRequest(BaseModel):
    """Payload for a chat turn."""

    message: str = Field(min_length=1)
    personality: str = DEFAULT_PERSONALITY
    conversation_id: int | None = None


def _sse(data: dict) -> str:
    """Format a dict as a Server-Sent Events ``data:`` frame."""
    return f"data: {json.dumps(data)}\n\n"


@app.get("/api/meta")
def get_meta() -> dict:
    """Expose model + personality metadata for the UI."""
    return {
        "model": settings.model,
        "default_personality": DEFAULT_PERSONALITY,
        "personalities": list_personalities(),
    }


@app.get("/api/conversations")
def get_conversations() -> list[dict]:
    """List saved conversations, most recently updated first."""
    return [
        {
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at.isoformat(),
            "message_count": c.message_count,
        }
        for c in store.list_conversations()
    ]


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: int) -> dict:
    """Return a single conversation's messages (with timestamps)."""
    try:
        messages = store.get_conversation_messages(conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": conversation_id, "messages": messages}


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: int) -> dict:
    """Delete a conversation and its messages."""
    deleted = store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True, "id": conversation_id}


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    """Stream an assistant reply as SSE frames.

    Frame types: ``token`` (incremental text), ``done`` (final metadata:
    conversation id + token usage), and ``error`` (graceful failure).
    """
    prompt = get_personality_prompt(request.personality)

    conversation_id = request.conversation_id
    if conversation_id is not None and not store.exists(conversation_id):
        conversation_id = None

    def event_stream() -> Iterator[str]:
        bot = Chatbot(
            settings,
            store=store,
            conversation_id=conversation_id,
            system_prompt=prompt,
        )
        try:
            for token in bot.stream(request.message):
                yield _sse({"type": "token", "content": token})
        except Exception as exc:  # noqa: BLE001 - report errors to the client
            yield _sse({"type": "error", "message": str(exc)})
            return

        done: dict = {"type": "done", "conversation_id": bot.conversation_id}
        usage = bot.last_usage
        if usage is not None:
            done["usage"] = {
                "prompt": usage.prompt_tokens,
                "completion": usage.completion_tokens,
                "total": usage.total_tokens,
                "cost": bot.estimate_cost(usage),
            }
        yield _sse(done)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Serve the frontend at the root. Registered last so the API routes above take
# precedence over the catch-all static mount.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
