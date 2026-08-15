from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import WeatherSnapshot


def upsert_weather_snapshot(
    session: Session, profile_id: str, for_date: date, **fields: object
) -> WeatherSnapshot:
    row = session.execute(
        select(WeatherSnapshot).where(
            WeatherSnapshot.profile_id == profile_id, WeatherSnapshot.for_date == for_date
        )
    ).scalar_one_or_none()
    if row is None:
        row = WeatherSnapshot(profile_id=profile_id, for_date=for_date)
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def list_weather_for_range(
    session: Session, profile_id: str, since: date, until: date
) -> list[WeatherSnapshot]:
    return list(
        session.execute(
            select(WeatherSnapshot)
            .where(
                WeatherSnapshot.profile_id == profile_id,
                WeatherSnapshot.for_date >= since,
                WeatherSnapshot.for_date <= until,
            )
            .order_by(WeatherSnapshot.for_date)
        ).scalars()
    )
