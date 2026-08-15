"""Synthetic Demo Mode data generator. See docs/PRODUCT_SPEC.md §76.

Generates several weeks of realistic-but-fake running/padel history, daily
health summaries, WHO-5 history, non-sensitive example lab results and body
composition, a busy upcoming-week calendar snapshot, and a previous
approved/partially-completed plan — enough to exercise a full Sunday Review
end to end without any real personal data.

Synthetic data here must never resemble the user's real (unentered) family
health history — no family_history_item rows are seeded, and lab results
are ordinary/non-alarming example values from a fictitious "Demo Lab".
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from sophie.repositories import (
    clinical_repo,
    health_intel_repo,
    planning_repo,
    profile_repo,
    summary_repo,
    workout_repo,
)

_SEED = 42
_WEEKS_OF_HISTORY = 8


@dataclass
class DemoSeedResult:
    profile_id: str
    weeks_seeded: int


def _monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def seed_demo_data(session: Session, as_of: date | None = None) -> DemoSeedResult:
    rng = random.Random(_SEED)
    today = as_of or date.today()
    profile = profile_repo.get_or_create_profile(session)

    profile_repo.update_config(
        session,
        profile.id,
        current_weight_kg=90.0,
        weight_goal_kg=79.0,
        race_name="Half marathon",
        race_date=date(2027, 5, 1),
        weather_location_name="Helsinki, Finland",
        weather_lat=60.1699,
        weather_lon=24.9384,
        active_block_name="Current 4-week half-marathon build",
    )

    # `this_monday` is the Monday of the week containing `today` — this is
    # exactly the "last week" sophie.domain.planner.week_start_for(today)'s
    # upcoming week looks back to (week_start_for(today) - 7 days ==
    # this_monday), i.e. the week the next Sunday Review reviews.
    this_monday = _monday_on_or_before(today)
    last_week_start = this_monday
    # History covers the WEEKS_OF_HISTORY-1 weeks strictly before last week;
    # last week itself is seeded separately by _seed_last_week so its plan
    # and actual workouts tell one coherent, intentional plan-vs-actual
    # story instead of two independently-generated (and possibly
    # contradictory) datasets.
    first_monday = last_week_start - timedelta(weeks=_WEEKS_OF_HISTORY - 1)

    weight = 91.5
    for week_index in range(_WEEKS_OF_HISTORY - 1):
        week_start = first_monday + timedelta(weeks=week_index)
        weight = _seed_week(session, profile.id, week_start, week_index, weight, rng)

    _seed_last_week(session, profile.id, last_week_start, _WEEKS_OF_HISTORY - 1, weight, rng)

    _seed_wellbeing_history(session, profile.id, this_monday)
    _seed_lab_results(session, profile.id, this_monday)
    _seed_body_composition(session, profile.id, this_monday)
    _seed_next_week_calendar(session, profile.id, this_monday)
    _seed_decision_log(session, profile.id, this_monday)

    return DemoSeedResult(profile_id=profile.id, weeks_seeded=_WEEKS_OF_HISTORY)


def _seed_week(
    session: Session,
    profile_id: str,
    week_start: date,
    week_index: int,
    weight_start: float,
    rng: random.Random,
) -> float:
    weight = weight_start
    block_pos = week_index % 4

    long_km = {0: 14.0, 1: 15.0, 2: 16.0, 3: 13.0}[block_pos]
    easy_km = {0: 8.5, 1: 9.5, 2: 10.0, 3: 8.0}[block_pos]
    quality_desc = {
        0: "6 x 250m uphill",
        1: "3 x 8min controlled threshold",
        2: "7 x 250m uphill",
        3: "3 x 6min controlled threshold",
    }[block_pos]

    # Thursday padel
    padel_day = week_start + timedelta(days=3)
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="padel",
        start_at=datetime.combine(padel_day, time(18, 30), tzinfo=UTC),
        duration_s=75 * 60,
        distance_m=None,
        avg_hr=128 + rng.randint(-4, 4),
        source_quality="single_source",
    )

    # Quality session (Tuesday)
    quality_day = week_start + timedelta(days=1)
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="run",
        start_at=datetime.combine(quality_day, time(8, 45), tzinfo=UTC),
        duration_s=45 * 60,
        distance_m=8000 + rng.randint(-300, 300),
        avg_hr=155 + rng.randint(-5, 5),
        max_hr=172 + rng.randint(-3, 3),
        avg_pace_s_per_km=300,
        notes=quality_desc,
    )

    # Easy run (Friday)
    easy_day = week_start + timedelta(days=4)
    easy_distance = easy_km * 1000 + rng.randint(-200, 200)
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="run",
        start_at=datetime.combine(easy_day, time(8, 45), tzinfo=UTC),
        duration_s=int(easy_distance / 1000 * 6.7 * 60),
        distance_m=easy_distance,
        avg_hr=138 + rng.randint(-5, 5),
        avg_pace_s_per_km=400 + rng.randint(-10, 10),
    )

    # Long run (Saturday), skip on the most recent (unfinished) week
    long_day = week_start + timedelta(days=5)
    long_distance = long_km * 1000 + rng.randint(-300, 300)
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="run",
        start_at=datetime.combine(long_day, time(9, 0), tzinfo=UTC),
        duration_s=int(long_distance / 1000 * 6.9 * 60),
        distance_m=long_distance,
        avg_hr=142 + rng.randint(-5, 5),
        avg_pace_s_per_km=414 + rng.randint(-10, 10),
    )

    # Daily health summaries for the week
    for day_offset in range(7):
        day = week_start + timedelta(days=day_offset)
        weight -= 0.03 + rng.uniform(-0.02, 0.04)
        summary_repo.upsert_daily_summary(
            session,
            profile_id,
            day,
            weight_kg=round(weight, 1) if day_offset == 0 else None,
            steps=7000 + rng.randint(-1500, 3000),
            walking_running_distance_m=5000 + rng.randint(-1000, 2000),
            active_energy_kcal=2400 + rng.randint(-200, 300),
            exercise_minutes=30 + rng.randint(-10, 40),
            resting_hr=54 + rng.randint(-3, 3) - week_index * 0.1,
            hrv_ms=52 + rng.randint(-6, 6),
            sleep_minutes=400 + rng.randint(-40, 40),
            sleep_efficiency=0.88 + rng.uniform(-0.05, 0.05),
            bedtime_local=f"{22 + rng.randint(0, 1)}:{rng.randint(0, 59):02d}",
            waketime_local=f"0{6 + rng.randint(0, 1)}:{rng.randint(0, 59):02d}",
            respiratory_rate=14.5 + rng.uniform(-0.5, 0.5),
            spo2_pct=97 + rng.uniform(-1, 1),
            daylight_minutes=90 + rng.randint(-30, 60),
            headphone_audio_db=(72 + rng.randint(-5, 8)) if rng.random() > 0.4 else None,
            environmental_audio_db=(68 + rng.randint(-5, 8)) if rng.random() > 0.4 else None,
            dietary_energy_kcal=(2600 + rng.randint(-200, 200)) if rng.random() > 0.3 else None,
            protein_g=(150 + rng.randint(-20, 20)) if rng.random() > 0.3 else None,
            carbs_g=(180 + rng.randint(-30, 30)) if rng.random() > 0.3 else None,
            fat_g=(90 + rng.randint(-15, 15)) if rng.random() > 0.3 else None,
            mindful_minutes=(10 if rng.random() > 0.6 else None),
        )
        if week_index % 2 == 0 and day_offset == 0:
            summary_repo.upsert_daily_summary(
                session, profile_id, day, vo2_max=42 + week_index * 0.15
            )

    return weight


def _seed_wellbeing_history(session: Session, profile_id: str, this_monday: date) -> None:
    # Deliberately shows wellbeing declining even while physical metrics
    # improve — the exact "not an overall successful trajectory" pattern
    # described in docs/PRODUCT_SPEC.md §26.
    scores = [80, 76, 68, 64]
    for i, pct in enumerate(scores):
        assessed_at = datetime.combine(
            this_monday - timedelta(weeks=(len(scores) - i) * 2), time(9, 0), tzinfo=UTC
        )
        health_intel_repo.add_wellbeing_assessment(
            session,
            profile_id=profile_id,
            assessed_at=assessed_at,
            instrument="WHO-5",
            instrument_version="1998-who-euro",
            raw_score=pct // 4,
            percentage_score=pct,
            answers=[pct // 4 // 5] * 5,
        )


def _seed_lab_results(session: Session, profile_id: str, this_monday: date) -> None:
    clinical_import = clinical_repo.create_clinical_import(
        session,
        profile_id=profile_id,
        provider="Demo Lab",
        source_kind="csv",
        imported_at=datetime.now(UTC),
        user_confirmed=True,
    )
    sample_date = this_monday - timedelta(weeks=20)
    rows = [
        ("Hemoglobin", "hemoglobin", "blood_count", 14.8, "g/dL", 13.0, 17.0, None),
        ("HbA1c", "hba1c", "glucose", 5.4, "%", 4.0, 6.0, None),
        ("LDL Cholesterol", "ldl_cholesterol", "lipids", 3.6, "mmol/L", 0.0, 3.0, "H"),
        ("HDL Cholesterol", "hdl_cholesterol", "lipids", 1.4, "mmol/L", 1.0, 999.0, None),
        ("TSH", "tsh", "thyroid", 2.1, "mIU/L", 0.4, 4.0, None),
        ("Ferritin", "ferritin", "iron", 95.0, "ug/L", 30.0, 400.0, None),
    ]
    for test_name, canonical_id, category, value, unit, low, high, flag in rows:
        clinical_repo.add_lab_result(
            session,
            profile_id=profile_id,
            clinical_import_id=clinical_import.id,
            sample_date=sample_date,
            test_name=test_name,
            canonical_test_id=canonical_id,
            value=value,
            value_text=None,
            unit=unit,
            reference_low=low,
            reference_high=high,
            reference_text=f"{low}-{high}",
            abnormal_flag=flag,
            category=category,
            notes=None,
        )


def _seed_body_composition(session: Session, profile_id: str, this_monday: date) -> None:
    clinical_repo.add_body_composition(
        session,
        profile_id=profile_id,
        assessed_at=this_monday - timedelta(weeks=10),
        method="bioimpedance-InBody",
        provider="Demo Wellness Clinic",
        weight_kg=91.0,
        body_fat_pct=24.5,
        lean_mass_kg=68.7,
        segmental_json=None,
        visceral_metric=9.0,
        notes=None,
    )


def _seed_last_week(
    session: Session,
    profile_id: str,
    week_start: date,
    week_index: int,
    weight_start: float,
    rng: random.Random,
) -> None:
    """The most recently completed week: an approved+calendar-written plan
    whose sessions have actual matching canonical_workout rows, telling one
    coherent plan-vs-actual story (quality/easy completed, long run only
    partially completed) instead of two independently-generated datasets."""

    block_pos = week_index % 4
    long_km = {0: 14.0, 1: 15.0, 2: 16.0, 3: 13.0}[block_pos]
    easy_km = {0: 8.5, 1: 9.5, 2: 10.0, 3: 8.0}[block_pos]
    quality_desc = {
        0: "6 x 250m uphill",
        1: "3 x 8min controlled threshold",
        2: "7 x 250m uphill",
        3: "3 x 6min controlled threshold",
    }[block_pos]

    plan = planning_repo.create_plan(
        session,
        profile_id,
        week_start,
        state="calendar_written",
        verdict="repeat",
        reasons=["Training load was elevated the prior week."],
        conservative_alternative={"summary": "One easy run only", "sessions": []},
        coach_note="Held steady rather than progressing.",
        llm_used=False,
        validation_notes=[],
    )

    quality_day = week_start + timedelta(days=1)
    padel_day = week_start + timedelta(days=3)
    easy_day = week_start + timedelta(days=4)
    long_day = week_start + timedelta(days=5)
    long_planned_m = long_km * 1000

    planned_sessions = [
        (quality_day, "quality", 45, 8000.0, "completed"),
        (easy_day, "easy", 50, easy_km * 1000, "completed"),
        (long_day, "long", 90, long_planned_m, "partial"),
    ]
    for day, session_type, duration, distance_m, status in planned_sessions:
        row = planning_repo.add_session(
            session,
            plan.id,
            date=day,
            time=time(8, 45),
            session_type=session_type,
            purpose=quality_desc if session_type == "quality" else "Demo session",
            distance_m=distance_m,
            estimated_duration_min=duration,
        )
        row.completion_status = status

    # Actual workouts: quality/easy completed close to plan, long run only ~65%.
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="padel",
        start_at=datetime.combine(padel_day, time(18, 30), tzinfo=UTC),
        duration_s=75 * 60,
        distance_m=None,
        avg_hr=128 + rng.randint(-4, 4),
    )
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="run",
        start_at=datetime.combine(quality_day, time(8, 45), tzinfo=UTC),
        duration_s=45 * 60,
        distance_m=8000,
        avg_hr=155 + rng.randint(-5, 5),
        max_hr=172,
        notes=quality_desc,
    )
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="run",
        start_at=datetime.combine(easy_day, time(8, 45), tzinfo=UTC),
        duration_s=int(easy_km * 6.7 * 60),
        distance_m=easy_km * 1000,
        avg_hr=138 + rng.randint(-5, 5),
    )
    workout_repo.create_canonical_workout(
        session,
        profile_id=profile_id,
        activity_type="run",
        start_at=datetime.combine(long_day, time(9, 0), tzinfo=UTC),
        duration_s=int(long_planned_m * 0.65 / 1000 * 6.9 * 60),
        distance_m=long_planned_m * 0.65,
        avg_hr=148 + rng.randint(-5, 5),
        notes="Cut short — felt tired.",
    )

    weight = weight_start
    for day_offset in range(7):
        day = week_start + timedelta(days=day_offset)
        weight -= 0.03 + rng.uniform(-0.02, 0.04)
        summary_repo.upsert_daily_summary(
            session,
            profile_id,
            day,
            weight_kg=round(weight, 1) if day_offset == 0 else None,
            steps=7000 + rng.randint(-1500, 3000),
            resting_hr=54 + rng.randint(-3, 3),
            hrv_ms=50 + rng.randint(-6, 6),
            sleep_minutes=395 + rng.randint(-40, 40),
            respiratory_rate=14.6 + rng.uniform(-0.5, 0.5),
            daylight_minutes=90 + rng.randint(-30, 60),
        )
    session.flush()


def _seed_next_week_calendar(session: Session, profile_id: str, this_monday: date) -> None:
    next_monday = this_monday + timedelta(weeks=1)
    busy = []
    for day_offset in range(5):  # Mon-Fri busy 09:00-17:00
        day = next_monday + timedelta(days=day_offset)
        start = datetime.combine(day, time(9, 0), tzinfo=UTC)
        end = datetime.combine(day, time(17, 0), tzinfo=UTC)
        busy.append({"start": start.isoformat(), "end": end.isoformat(), "all_day": False})
    padel_day = next_monday + timedelta(days=3)
    busy.append(
        {
            "start": datetime.combine(padel_day, time(18, 0), tzinfo=UTC).isoformat(),
            "end": datetime.combine(padel_day, time(19, 30), tzinfo=UTC).isoformat(),
            "all_day": False,
        }
    )
    planning_repo.save_calendar_snapshot(session, profile_id, next_monday, busy, source="mock")


def _seed_decision_log(session: Session, profile_id: str, this_monday: date) -> None:
    verdicts = ["build", "build", "repeat", "reduce"]
    for i, verdict in enumerate(verdicts):
        week_start = this_monday - timedelta(weeks=len(verdicts) - i)
        planning_repo.add_decision_log_entry(
            session,
            profile_id=profile_id,
            week_start=week_start,
            verdict=verdict,
            recommended_plan_ref=None,
            approved_plan_ref=None,
            actual_result_summary="Completed as planned"
            if verdict == "build"
            else "Partially completed",
            training_load_status="typical" if verdict != "reduce" else "elevated",
            data_quality_summary="sufficient",
            coach_note="Demo week.",
            calendar_write_state="calendar_written",
        )
