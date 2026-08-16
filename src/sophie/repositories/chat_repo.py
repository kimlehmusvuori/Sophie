from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import ChatMessage


def add_message(
    session: Session, profile_id: str, role: str, content: str, provider: str | None = None
) -> ChatMessage:
    message = ChatMessage(profile_id=profile_id, role=role, content=content, provider=provider)
    session.add(message)
    session.flush()
    return message


def list_messages(session: Session, profile_id: str, limit: int = 50) -> list[ChatMessage]:
    return list(
        session.execute(
            select(ChatMessage)
            .where(ChatMessage.profile_id == profile_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )[::-1]


def clear_messages(session: Session, profile_id: str) -> None:
    for message in session.execute(
        select(ChatMessage).where(ChatMessage.profile_id == profile_id)
    ).scalars():
        session.delete(message)
    session.flush()
