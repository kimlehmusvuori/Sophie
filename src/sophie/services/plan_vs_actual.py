"""Matches approved plan sessions against imported canonical workouts. See
docs/PRODUCT_SPEC.md §52: ambiguous matches are never guessed at — they're
reported back for the user to resolve, and clearly unmatched planned
sessions become "missed" rather than silently disappearing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session as OrmSession

from sophie.db.models import CanonicalWorkout
from sophie.db.models import Session as SessionModel
from sophie.repositories import planning_repo, workout_repo

_DATE_WINDOW_DAYS = 2
_DISTANCE_TOLERANCE = 0.25  # 25% either side counts as "completed as planned"
_PARTIAL_THRESHOLD = 0.7  # actual distance below 70% of planned counts as "partial"

# A planned session's `session_type` (long/quality/easy/padel/other, see
# sophie.domain.training_block.SessionType) describes plan *intent* — the
# actual recorded canonical_workout.activity_type is always one of
# run/padel/cycling/tennis/strength/other (see sophie.domain.activity_types).
# Long/quality/easy plans are all satisfied by an actual "run" workout.
_SESSION_TYPE_TO_ACTIVITY_TYPE = {
    "long": "run",
    "quality": "run",
    "easy": "run",
    "padel": "padel",
    "other": "other",
}


def _expected_activity_type(session_type: str) -> str:
    return _SESSION_TYPE_TO_ACTIVITY_TYPE.get(session_type, session_type)


@dataclass
class SessionMatchResult:
    session_id: str
    status: str  # completed/partial/moved/missed/ambiguous
    matched_workout_id: str | None = None


@dataclass
class PlanVsActualResult:
    session_results: list[SessionMatchResult] = field(default_factory=list)
    extra_unplanned_workout_ids: list[str] = field(default_factory=list)


def match_plan_to_actuals(
    orm_session: OrmSession, plan_id: str, profile_id: str
) -> PlanVsActualResult:
    sessions = planning_repo.list_sessions_for_plan(orm_session, plan_id)
    if not sessions:
        return PlanVsActualResult()

    window_start = min(s.date for s in sessions) - timedelta(days=_DATE_WINDOW_DAYS)
    window_end = max(s.date for s in sessions) + timedelta(days=_DATE_WINDOW_DAYS)
    candidate_workouts = [
        w
        for w in workout_repo.list_workouts(orm_session, profile_id)
        if window_start <= w.start_at.date() <= window_end
    ]

    consumed_ids: set[str] = set()
    results: list[SessionMatchResult] = []

    for planned in sorted(sessions, key=lambda s: s.date):
        expected_activity_type = _expected_activity_type(planned.session_type)
        matches = [
            w
            for w in candidate_workouts
            if w.id not in consumed_ids
            and w.activity_type == expected_activity_type
            and abs((w.start_at.date() - planned.date).days) <= _DATE_WINDOW_DAYS
        ]

        if not matches:
            status = "missed"
            matched_id = None
        elif len(matches) > 1:
            status = "ambiguous"
            matched_id = None
        else:
            workout = matches[0]
            matched_id = workout.id
            consumed_ids.add(workout.id)
            status = _classify_single_match(planned, workout)

        planned.completion_status = status
        planned.matched_workout_id = matched_id
        results.append(
            SessionMatchResult(session_id=planned.id, status=status, matched_workout_id=matched_id)
        )

    orm_session.flush()

    extras = [w.id for w in candidate_workouts if w.id not in consumed_ids]
    return PlanVsActualResult(session_results=results, extra_unplanned_workout_ids=extras)


def _classify_single_match(planned: SessionModel, workout: CanonicalWorkout) -> str:
    if workout.start_at.date() != planned.date:
        return "moved"
    if planned.distance_m is None or workout.distance_m is None:
        return "completed"
    ratio = workout.distance_m / planned.distance_m if planned.distance_m else 0
    if ratio < _PARTIAL_THRESHOLD:
        return "partial"
    if abs(ratio - 1) <= _DISTANCE_TOLERANCE:
        return "completed"
    return "completed" if ratio > 1 else "partial"
