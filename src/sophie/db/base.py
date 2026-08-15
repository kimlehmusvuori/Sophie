"""SQLAlchemy engine/session plumbing. This is the only module that should
construct engines directly."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    """Stable UUID primary key for user-owned aggregate roots."""

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


def new_uuid() -> str:
    return str(uuid.uuid4())


_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, future=True)
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def configure(database_url: str) -> None:
    """(Re)configure the process-wide engine/session factory. Used at app startup
    and in tests to point at a fresh temp database."""
    global _engine, _SessionFactory
    _engine = build_engine(database_url)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database not configured — call sophie.db.base.configure() first")
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope for multi-step state changes."""
    if _SessionFactory is None:
        raise RuntimeError("Database not configured — call sophie.db.base.configure() first")
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
