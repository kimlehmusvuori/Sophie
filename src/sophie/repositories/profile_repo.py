from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import FamilyHistoryItem, Profile, UserConfig


def get_or_create_profile(session: Session) -> Profile:
    profile = session.execute(select(Profile).limit(1)).scalar_one_or_none()
    if profile is not None:
        return profile
    profile = Profile()
    session.add(profile)
    session.flush()
    config = UserConfig(profile_id=profile.id, updated_at=datetime.now(UTC))
    session.add(config)
    session.flush()
    return profile


def get_config(session: Session, profile_id: str) -> UserConfig:
    config = session.execute(
        select(UserConfig).where(UserConfig.profile_id == profile_id)
    ).scalar_one_or_none()
    if config is None:
        config = UserConfig(profile_id=profile_id, updated_at=datetime.now(UTC))
        session.add(config)
        session.flush()
    return config


def update_config(session: Session, profile_id: str, **fields: object) -> UserConfig:
    config = get_config(session, profile_id)
    for key, value in fields.items():
        if hasattr(config, key):
            setattr(config, key, value)
    config.updated_at = datetime.now(UTC)
    session.flush()
    return config


def list_family_history(session: Session, profile_id: str) -> list[FamilyHistoryItem]:
    return list(
        session.execute(
            select(FamilyHistoryItem).where(FamilyHistoryItem.profile_id == profile_id)
        ).scalars()
    )


def add_family_history_item(
    session: Session, profile_id: str, category: str, note: str | None
) -> FamilyHistoryItem:
    item = FamilyHistoryItem(
        profile_id=profile_id, category=category, note=note, entered_at=datetime.now(UTC)
    )
    session.add(item)
    session.flush()
    return item


def delete_family_history_item(session: Session, item_id: str) -> None:
    item = session.get(FamilyHistoryItem, item_id)
    if item is not None:
        session.delete(item)
        session.flush()
