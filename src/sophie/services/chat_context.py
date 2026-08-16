"""Assembles the sanitized ChatContext for the free-form Chat feature. This
is the single place that decides what the chat LLM is allowed to see — see
docs/PRIVACY.md. Every input here is an already-derived summary/status
value (health-intelligence snapshot, trailing-window averages over
DailyHealthSummary, user-entered goals/preferences) — there is no path from
a raw import table into this function."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from sophie.domain.chat_types import ChatContext, MetricAverage
from sophie.domain.coach_types import DomainStatus
from sophie.repositories import profile_repo, summary_repo
from sophie.services import health_intelligence

_METRIC_WINDOW_DAYS = 30


def _domain_statuses_from_snapshot(
    snapshot: health_intelligence.HealthIntelligenceSnapshot,
) -> list[DomainStatus]:
    wellbeing_quality = (
        "insufficient" if snapshot.wellbeing.get("trend") == "insufficient_data" else "sufficient"
    )
    return [
        DomainStatus(
            domain="cardiovascular",
            status=snapshot.cardio_trend.overall_trend,
            data_quality=snapshot.cardio_trend.data_quality,
        ),
        DomainStatus(
            domain="training_load",
            status=snapshot.training_load.status,
            data_quality=snapshot.training_load.data_quality,
        ),
        DomainStatus(
            domain="recovery",
            status=snapshot.recovery.status,
            data_quality=snapshot.recovery.data_quality,
        ),
        DomainStatus(
            domain="aerobic_efficiency",
            status=snapshot.aerobic_efficiency_trend.trend,
            data_quality=snapshot.aerobic_efficiency_trend.data_quality,
        ),
        DomainStatus(
            domain="everyday_movement",
            status=snapshot.movement.status,
            data_quality=snapshot.movement.data_quality,
        ),
        DomainStatus(
            domain="circadian",
            status="tracked"
            if snapshot.circadian.data_quality != "insufficient"
            else "insufficient_data",
            data_quality=snapshot.circadian.data_quality,
        ),
        DomainStatus(
            domain="hearing",
            status="tracked"
            if snapshot.hearing.data_quality != "insufficient"
            else "insufficient_data",
            data_quality=snapshot.hearing.data_quality,
        ),
        DomainStatus(
            domain="mental_wellbeing",
            status=str(snapshot.wellbeing.get("trend", "insufficient_data")),
            data_quality=wellbeing_quality,
        ),
    ]


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _metric_average(
    label: str, values: list[float | None], unit: str, window_days: int
) -> MetricAverage:
    present = [v for v in values if v is not None]
    return MetricAverage(
        label=label,
        value=_average(present),
        unit=unit,
        window_days=window_days,
        days_with_data=len(present),
    )


def _trailing_metric_averages(
    session: Session, profile_id: str, today: date
) -> list[MetricAverage]:
    since = today - timedelta(days=_METRIC_WINDOW_DAYS - 1)
    daily = summary_repo.list_daily_summaries(session, profile_id, since, today)

    return [
        _metric_average(
            "sleep duration", [d.sleep_minutes for d in daily], "min/night", _METRIC_WINDOW_DAYS
        ),
        _metric_average(
            "resting heart rate", [d.resting_hr for d in daily], "bpm", _METRIC_WINDOW_DAYS
        ),
        _metric_average("HRV", [d.hrv_ms for d in daily], "ms", _METRIC_WINDOW_DAYS),
        _metric_average("weight", [d.weight_kg for d in daily], "kg", _METRIC_WINDOW_DAYS),
        _metric_average(
            "daily steps",
            [float(d.steps) if d.steps is not None else None for d in daily],
            "steps",
            _METRIC_WINDOW_DAYS,
        ),
    ]


def build_chat_context(session: Session, profile_id: str, today: date | None = None) -> ChatContext:
    today = today or date.today()
    config = profile_repo.get_config(session, profile_id)
    snapshot = health_intelligence.refresh_all_health_intelligence(session, profile_id, today)

    return ChatContext(
        domain_statuses=_domain_statuses_from_snapshot(snapshot),
        metric_averages=_trailing_metric_averages(session, profile_id, today),
        race_name=config.race_name,
        race_date=config.race_date,
        weight_goal_kg=config.weight_goal_kg,
        current_weight_kg=config.current_weight_kg,
        max_runs_per_week=config.max_runs_per_week,
        sophie_memory=config.sophie_memory,
        explicit_exclusions=config.explicit_exclusions or [],
    )
