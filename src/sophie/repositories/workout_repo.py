from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import CanonicalWorkout, WorkoutSourceProvenance

_MATCH_WINDOW = timedelta(minutes=20)


def find_matching_workout(
    session: Session,
    profile_id: str,
    activity_type: str,
    start_at: datetime,
    distance_m: float | None,
) -> CanonicalWorkout | None:
    """Deterministic cross-source match: same profile, same activity type,
    start time within a small tolerance window, and (if both known) distance
    within 10%. Ambiguous cases are left for the caller to handle explicitly
    rather than silently merged."""

    candidates = (
        session.execute(
            select(CanonicalWorkout).where(
                CanonicalWorkout.profile_id == profile_id,
                CanonicalWorkout.activity_type == activity_type,
                CanonicalWorkout.start_at >= start_at - _MATCH_WINDOW,
                CanonicalWorkout.start_at <= start_at + _MATCH_WINDOW,
            )
        )
        .scalars()
        .all()
    )

    if not candidates:
        return None
    if len(candidates) == 1:
        candidate = candidates[0]
    else:
        candidate = min(candidates, key=lambda c: abs((c.start_at - start_at).total_seconds()))

    if distance_m is not None and candidate.distance_m is not None:
        ratio = distance_m / candidate.distance_m if candidate.distance_m else 0
        if not (0.9 <= ratio <= 1.1):
            return None
    return candidate


def create_canonical_workout(session: Session, **fields: object) -> CanonicalWorkout:
    workout = CanonicalWorkout(**fields)
    session.add(workout)
    session.flush()
    return workout


def add_provenance(session: Session, **fields: object) -> WorkoutSourceProvenance:
    provenance = WorkoutSourceProvenance(**fields)
    session.add(provenance)
    session.flush()
    return provenance


def list_workouts(
    session: Session, profile_id: str, since: datetime | None = None, until: datetime | None = None
) -> list[CanonicalWorkout]:
    stmt = select(CanonicalWorkout).where(CanonicalWorkout.profile_id == profile_id)
    if since is not None:
        stmt = stmt.where(CanonicalWorkout.start_at >= since)
    if until is not None:
        stmt = stmt.where(CanonicalWorkout.start_at <= until)
    stmt = stmt.order_by(CanonicalWorkout.start_at)
    return list(session.execute(stmt).scalars())
