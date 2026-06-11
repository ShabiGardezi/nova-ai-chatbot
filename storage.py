"""SQLite-backed conversation persistence using SQLAlchemy.

Defines the ORM models (``Conversation`` and ``MessageRecord``) and a
``ConversationStore`` repository that exposes a small, clean API for saving,
listing, resuming, and deleting conversations. The rest of the app depends
only on ``ConversationStore`` and never touches the ORM directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, create_engine, func, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    messages: Mapped[list["MessageRecord"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageRecord.id",
    )


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    """Lightweight view of a conversation for listings."""

    id: int
    title: str
    updated_at: datetime
    message_count: int


class ConversationStore:
    """Repository for persisting and retrieving conversations."""

    def __init__(self, database_url: str = "sqlite:///chatbot.db") -> None:
        self._engine = create_engine(database_url)
        Base.metadata.create_all(self._engine)

    def create_conversation(self, title: str | None = None) -> int:
        """Create a conversation row and return its id."""
        with Session(self._engine) as session:
            conversation = Conversation(title=(title or "New conversation"))
            session.add(conversation)
            session.commit()
            return conversation.id

    def add_message(self, conversation_id: int, role: str, content: str) -> None:
        """Append a message to a conversation and bump its ``updated_at``."""
        with Session(self._engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                raise KeyError(f"Conversation {conversation_id} not found.")
            conversation.messages.append(MessageRecord(role=role, content=content))
            conversation.updated_at = _utcnow()
            session.commit()

    def get_messages(self, conversation_id: int) -> list[tuple[str, str]]:
        """Return ``(role, content)`` pairs in insertion order."""
        with Session(self._engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                raise KeyError(f"Conversation {conversation_id} not found.")
            return [(m.role, m.content) for m in conversation.messages]

    def get_conversation_messages(self, conversation_id: int) -> list[dict[str, str]]:
        """Return messages as serializable dicts (with ISO timestamps).

        Intended for the web API, where the frontend needs ``created_at`` to
        render message timestamps. Raises ``KeyError`` if the id is unknown.
        """
        with Session(self._engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                raise KeyError(f"Conversation {conversation_id} not found.")
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in conversation.messages
            ]

    def list_conversations(self) -> list[ConversationSummary]:
        """Return all conversations, most recently updated first."""
        stmt = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.updated_at,
                func.count(MessageRecord.id),
            )
            .outerjoin(MessageRecord)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
        )
        with Session(self._engine) as session:
            rows = session.execute(stmt).all()
        return [
            ConversationSummary(
                id=row[0],
                title=row[1],
                updated_at=row[2],
                message_count=row[3],
            )
            for row in rows
        ]

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation (and its messages). Returns ``False`` if absent."""
        with Session(self._engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                return False
            session.delete(conversation)
            session.commit()
            return True

    def exists(self, conversation_id: int) -> bool:
        with Session(self._engine) as session:
            return session.get(Conversation, conversation_id) is not None
