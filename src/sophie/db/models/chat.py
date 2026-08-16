from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, TimestampMixin, UUIDPKMixin


class ChatMessage(Base, UUIDPKMixin, TimestampMixin):
    """One turn in the free-form Chat page. Only ever holds the user's
    question and the LLM's (already safety-filtered) answer text — never the
    sanitized context object itself, which is rebuilt fresh per question."""

    __tablename__ = "chat_message"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user/assistant
    provider: Mapped[str | None] = mapped_column(String(20), default=None)  # set on assistant rows
    content: Mapped[str] = mapped_column()
