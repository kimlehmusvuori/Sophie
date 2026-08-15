"""Health-intelligence orchestration: turns the raw/summary rows already
persisted (`canonical_workout`, `daily_health_summary`, `lab_result`, ...)
into each health domain's current status by calling the pure functions in
`sophie.domain.*` and persisting the result via `sophie.repositories.*`.

This module never runs raw SQL, never touches SQLAlchemy models except
through repositories, never imports Streamlit, and never calls an LLM or the
network — it is pure orchestration/plumbing between real data and the
already-tested domain logic. See docs/ARCHITECTURE.md and
docs/HEALTH_LOGIC_AND_SAFETY.md.

Note on aerobic efficiency: `canonical_workout.activity_type` only
distinguishes broad activity kind (run/padel/cycling/tennis/strength/other);
Sophie does not (yet) tag an individual completed run as long/quality/easy on
that table (that classification lives on the *planned* `session` row, not the
canonical workout). So every completed "run" with both pace and heart rate is
treated as the domain's default "easy" comparable group — the same default
`aerobic_efficiency.compute_aerobic_efficiency_trend` already assumes when no
other classification is supplied. This is a known limitation, not a silent
invention: a future pass that threads `session.session_type` through
`matched_workout_id` could narrow this further.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from sophie.db.models import (
    AerobicEfficiencyPoint,
    CanonicalWorkout,
    CircadianSummary,
    HearingSummary,
    MovementBaseline,
    RecoverySummary,
    TrainingLoadSummary,
)
from sophie.domain import (
    aerobic_efficiency,
    cardio,
    circadian,
    hearing,
    movement,
    recovery,
    wellbeing,
)
from sophie.domain import training_load as training_load_domain
from sophie.repositories import (
    clinical_repo,
    health_intel_repo,
    profile_repo,
    summary_repo,
    workout_repo,
)

_TRAINING_LOAD_LOOKBACK_WEEKS = 5
_RECOVERY_LOOKBACK_DAYS = 90
_CIRCADIAN_LOOKBACK_DAYS = 14
_MOVEMENT_RECENT_DAYS = 7
_MOVEMENT_HISTORY_DAYS = 60
_HEARING_DEFAULT_LOOKBACK_DAYS = 90
_WIDE_RANGE_START = date(1900, 1, 1)
_WIDE_RANGE_END = date(2100, 1, 1)


def _week_start(as_of_date: date) -> date:
    """Monday on/before `as_of_date`."""
    return as_of_date - timedelta(days=as_of_date.weekday())


def _day_bounds_to_datetime(since: date, until: date) -> tuple[datetime, datetime]:
    since_dt = datetime.combine(since, time.min, tzinfo=UTC)
    until_dt = datetime.combine(until, time.max, tzinfo=UTC)
    return since_dt, until_dt


def _parse_hhmm_to_minutes(value: str | None) -> float | None:
    """Parses a "HH:MM" local-time string literally as minutes since
    midnight (e.g. "23:30" -> 1410), per `circadian.NightlySleep`'s
    convention (confirmed by its own tests)."""
    if not value:
        return None
    try:
        hours_str, minutes_str = value.split(":")
        return int(hours_str) * 60 + int(minutes_str)
    except (ValueError, AttributeError):
        return None


def refresh_training_load(
    session: Session, profile_id: str, as_of_date: date
) -> TrainingLoadSummary:
    """Pulls ~5 weeks of canonical workouts, computes this week's relative
    training load vs. the trailing baseline, and persists it for the week
    starting on the Monday on/before `as_of_date`."""

    since_dt, until_dt = _day_bounds_to_datetime(
        as_of_date - timedelta(weeks=_TRAINING_LOAD_LOOKBACK_WEEKS), as_of_date
    )
    workouts = workout_repo.list_workouts(session, profile_id, since=since_dt, until=until_dt)

    load_sessions = []
    for workout in workouts:
        if workout.duration_s is None:
            continue
        load_sessions.append(
            training_load_domain.LoadSession(
                day=workout.start_at.date(),
                activity_type=workout.activity_type,
                duration_min=workout.duration_s / 60.0,
                avg_hr=workout.avg_hr,
                # No personal resting/max-HR baseline is available to derive
                # a grounded hr_reserve_pct here, so the domain's
                # per-activity-type default intensity is used instead (see
                # module docstring).
                hr_reserve_pct=None,
            )
        )

    result = training_load_domain.compute_training_load(load_sessions, as_of=as_of_date)

    return health_intel_repo.upsert_training_load(
        session,
        profile_id,
        _week_start(as_of_date),
        status=result.status,
        load_ratio=result.load_ratio,
        evidence=result.evidence,
        calculation_version=result.calculation_version,
        data_quality=result.data_quality,
    )


def refresh_recovery(session: Session, profile_id: str, as_of_date: date) -> RecoverySummary:
    """Pulls ~90 trailing days of daily summaries, splits into "today" and
    "history", and persists the deviation status for `as_of_date`."""

    since = as_of_date - timedelta(days=_RECOVERY_LOOKBACK_DAYS)
    rows = summary_repo.list_daily_summaries(session, profile_id, since=since, until=as_of_date)

    today_row = next((row for row in rows if row.day == as_of_date), None)
    if today_row is not None:
        today_signals = recovery.DailySignals(
            day=as_of_date,
            resting_hr=today_row.resting_hr,
            hrv_ms=today_row.hrv_ms,
            sleep_minutes=today_row.sleep_minutes,
            respiratory_rate=today_row.respiratory_rate,
            wrist_temp_deviation_c=today_row.wrist_temp_deviation_c,
        )
    else:
        today_signals = recovery.DailySignals(day=as_of_date)

    history = [
        recovery.DailySignals(
            day=row.day,
            resting_hr=row.resting_hr,
            hrv_ms=row.hrv_ms,
            sleep_minutes=row.sleep_minutes,
            respiratory_rate=row.respiratory_rate,
            wrist_temp_deviation_c=row.wrist_temp_deviation_c,
        )
        for row in rows
        if row.day != as_of_date
    ]

    result = recovery.compute_recovery(today_signals, history)

    return health_intel_repo.upsert_recovery(
        session,
        profile_id,
        as_of_date,
        status=result.status,
        signals=result.signals,
        calculation_version=result.calculation_version,
        data_quality=result.data_quality,
    )


def refresh_circadian(session: Session, profile_id: str, as_of_date: date) -> CircadianSummary:
    """Pulls ~14 trailing days of bedtime/waketime and persists the
    circadian-regularity summary for the week starting on the Monday
    on/before `as_of_date`."""

    since = as_of_date - timedelta(days=_CIRCADIAN_LOOKBACK_DAYS - 1)
    rows = summary_repo.list_daily_summaries(session, profile_id, since=since, until=as_of_date)

    nights = [
        circadian.NightlySleep(
            day=row.day,
            bedtime_minutes_from_midnight=_parse_hhmm_to_minutes(row.bedtime_local),
            waketime_minutes_from_midnight=_parse_hhmm_to_minutes(row.waketime_local),
            sleep_minutes=row.sleep_minutes,
            daylight_minutes=row.daylight_minutes,
        )
        for row in rows
    ]

    result = circadian.compute_circadian_summary(nights)
    sleep_midpoint_local = (
        result.sleep_midpoint.strftime("%H:%M") if result.sleep_midpoint is not None else None
    )

    return health_intel_repo.upsert_circadian(
        session,
        profile_id,
        _week_start(as_of_date),
        bedtime_variability_min=result.bedtime_variability_min,
        waketime_variability_min=result.waketime_variability_min,
        sleep_midpoint_local=sleep_midpoint_local,
        duration_consistency=result.duration_consistency,
        disrupted_nights=result.disrupted_nights,
        avg_daylight_minutes=result.avg_daylight_minutes,
        data_quality=result.data_quality,
    )


def refresh_movement(session: Session, profile_id: str, as_of_date: date) -> MovementBaseline:
    """Pulls the trailing 7 days (recent) and trailing ~60 days (history) of
    step counts and persists the movement-baseline status for the week
    starting on the Monday on/before `as_of_date`."""

    recent_since = as_of_date - timedelta(days=_MOVEMENT_RECENT_DAYS - 1)
    history_since = as_of_date - timedelta(days=_MOVEMENT_HISTORY_DAYS - 1)

    recent_rows = summary_repo.list_daily_summaries(
        session, profile_id, since=recent_since, until=as_of_date
    )
    history_rows = summary_repo.list_daily_summaries(
        session, profile_id, since=history_since, until=as_of_date
    )

    recent = [movement.DailySteps(day=row.day, steps=row.steps) for row in recent_rows]
    history = [movement.DailySteps(day=row.day, steps=row.steps) for row in history_rows]

    result = movement.compute_movement_baseline(recent, history)

    return health_intel_repo.upsert_movement_baseline(
        session,
        profile_id,
        _week_start(as_of_date),
        avg_daily_steps=result.avg_daily_steps,
        personal_baseline_steps=result.personal_baseline_steps,
        status=result.status,
        data_quality=result.data_quality,
    )


def refresh_hearing(
    session: Session, profile_id: str, period_start: date, period_end: date
) -> HearingSummary:
    """Pulls daily summaries in `[period_start, period_end]` and persists the
    hearing/noise-exposure summary for that period."""

    rows = summary_repo.list_daily_summaries(
        session, profile_id, since=period_start, until=period_end
    )

    days = [
        hearing.DailyAudioExposure(
            day=row.day,
            headphone_avg_db=row.headphone_audio_db,
            environmental_avg_db=row.environmental_audio_db,
        )
        for row in rows
    ]

    result = hearing.summarize_hearing_exposure(days)

    return health_intel_repo.upsert_hearing_summary(
        session,
        profile_id,
        period_start,
        period_end,
        headphone_avg_db=result.headphone_avg_db,
        environmental_avg_db=result.environmental_avg_db,
        exposure_events=result.exposure_events,
        data_quality=result.data_quality,
    )


def compute_aerobic_efficiency(
    session: Session, profile_id: str
) -> aerobic_efficiency.EfficiencyTrend:
    """Builds the aerobic-efficiency trend from all canonical running
    workouts with both pace and heart rate present, and persists one
    `AerobicEfficiencyPoint` per workout that doesn't already have one
    (re-running this is idempotent — no duplicate points)."""

    workouts = workout_repo.list_workouts(session, profile_id)
    existing_workout_ids = {
        point.workout_id
        for point in health_intel_repo.list_aerobic_efficiency_points(session, profile_id)
    }

    # (workout, pace, avg_hr) — filtered/narrowed together so pace/avg_hr are
    # known non-None from here on, without re-asserting Optional fields.
    eligible: list[tuple[CanonicalWorkout, float, float]] = []
    for workout in workouts:
        if (
            workout.activity_type == "run"
            and workout.avg_pace_s_per_km is not None
            and workout.avg_hr is not None
        ):
            eligible.append((workout, workout.avg_pace_s_per_km, workout.avg_hr))

    runs = [
        aerobic_efficiency.EfficiencyRun(
            day=workout.start_at.date(),
            pace_s_per_km=pace,
            avg_hr=avg_hr,
            duration_min=(workout.duration_s / 60.0) if workout.duration_s is not None else 0.0,
            comparable_group="easy",
        )
        for workout, pace, avg_hr in eligible
    ]

    trend = aerobic_efficiency.compute_aerobic_efficiency_trend(runs)

    # Match each computed point back to the workout(s) it came from via
    # (day, efficiency_proxy) — both are derived deterministically from the
    # same pace/HR values, so this recovers the 1:1 correspondence without
    # duplicating the domain module's private duration-filter constant.
    candidates_by_key: dict[tuple[date, float], list[tuple[CanonicalWorkout, float, float]]] = {}
    for workout, pace, avg_hr in eligible:
        proxy = round(pace / avg_hr, 4)
        candidates_by_key.setdefault((workout.start_at.date(), proxy), []).append(
            (workout, pace, avg_hr)
        )

    new_points = []
    for point in trend.points:
        candidates = candidates_by_key.get((point.day, point.efficiency_proxy), [])
        for workout, pace, avg_hr in candidates:
            if workout.id in existing_workout_ids:
                continue
            new_points.append(
                AerobicEfficiencyPoint(
                    profile_id=profile_id,
                    workout_id=workout.id,
                    week_start=_week_start(point.day),
                    pace_s_per_km=pace,
                    avg_hr=avg_hr,
                    efficiency_proxy=point.efficiency_proxy,
                    comparable_group="easy",
                )
            )
            existing_workout_ids.add(workout.id)
            break

    if new_points:
        health_intel_repo.add_aerobic_efficiency_points(session, new_points)

    return trend


def compute_cardio_trend(session: Session, profile_id: str) -> cardio.CardioResult:
    """Builds the cardio/metabolic trajectory from VO2max, resting HR, and
    weight series plus lab-supplied abnormal flags. Cheap to compute — no
    dedicated persisted table, callers should call this fresh each time."""

    rows = summary_repo.list_daily_summaries(
        session, profile_id, since=_WIDE_RANGE_START, until=_WIDE_RANGE_END
    )
    vo2_max_series = [row.vo2_max for row in rows if row.vo2_max is not None]
    resting_hr_series = [row.resting_hr for row in rows if row.resting_hr is not None]
    weight_series = [row.weight_kg for row in rows if row.weight_kg is not None]

    config = profile_repo.get_config(session, profile_id)

    lab_results = clinical_repo.list_lab_results(session, profile_id)
    lab_abnormal_flags = sorted(
        {result.test_name for result in lab_results if result.abnormal_flag is not None}
    )

    inputs = cardio.CardioInputs(
        vo2_max_series=vo2_max_series,
        resting_hr_series=resting_hr_series,
        weight_series=weight_series,
        weight_goal_kg=config.weight_goal_kg,
        lab_abnormal_flags=lab_abnormal_flags,
    )

    return cardio.compute_cardio_trend(inputs)


def wellbeing_status(session: Session, profile_id: str, today: date) -> dict[str, object]:
    """Reports current WHO-5 status (due-ness + trend) without recording a
    new submission — that's a separate, explicit UI action."""

    assessments = health_intel_repo.list_wellbeing_assessments(session, profile_id)
    last_assessed_at = assessments[-1].assessed_at.date() if assessments else None
    scores = [
        (assessment.assessed_at.date(), assessment.percentage_score) for assessment in assessments
    ]

    return {
        "due": wellbeing.is_assessment_due(last_assessed_at, today),
        "trend": wellbeing.wellbeing_trend(scores),
        "latest_percentage": assessments[-1].percentage_score if assessments else None,
    }


@dataclass
class HealthIntelligenceSnapshot:
    training_load: TrainingLoadSummary
    recovery: RecoverySummary
    circadian: CircadianSummary
    movement: MovementBaseline
    hearing: HearingSummary
    aerobic_efficiency_trend: aerobic_efficiency.EfficiencyTrend
    cardio_trend: cardio.CardioResult
    wellbeing: dict[str, object]


def refresh_all_health_intelligence(
    session: Session, profile_id: str, as_of_date: date
) -> HealthIntelligenceSnapshot:
    """Convenience entry point: refreshes/computes every health-intelligence
    domain for `as_of_date` in one call. This is what a future Sunday Review
    calls before building coach context."""

    training_load_row = refresh_training_load(session, profile_id, as_of_date)
    recovery_row = refresh_recovery(session, profile_id, as_of_date)
    circadian_row = refresh_circadian(session, profile_id, as_of_date)
    movement_row = refresh_movement(session, profile_id, as_of_date)
    hearing_row = refresh_hearing(
        session,
        profile_id,
        as_of_date - timedelta(days=_HEARING_DEFAULT_LOOKBACK_DAYS - 1),
        as_of_date,
    )
    aerobic_trend = compute_aerobic_efficiency(session, profile_id)
    cardio_trend = compute_cardio_trend(session, profile_id)
    wellbeing_result = wellbeing_status(session, profile_id, as_of_date)

    return HealthIntelligenceSnapshot(
        training_load=training_load_row,
        recovery=recovery_row,
        circadian=circadian_row,
        movement=movement_row,
        hearing=hearing_row,
        aerobic_efficiency_trend=aerobic_trend,
        cardio_trend=cardio_trend,
        wellbeing=wellbeing_result,
    )
