from __future__ import annotations

from datetime import date

from sophie.repositories import (
    clinical_repo,
    health_intel_repo,
    planning_repo,
    profile_repo,
    workout_repo,
)
from sophie.services.demo_data import seed_demo_data


def test_seed_demo_data_populates_everything(db_session):
    result = seed_demo_data(db_session, as_of=date(2026, 8, 15))

    assert result.weeks_seeded == 8

    workouts = workout_repo.list_workouts(db_session, result.profile_id)
    assert len(workouts) >= 8 * 4  # padel + quality + easy + long per week

    assessments = health_intel_repo.list_wellbeing_assessments(db_session, result.profile_id)
    assert len(assessments) == 4
    assert assessments[0].percentage_score > assessments[-1].percentage_score  # declining trend

    labs = clinical_repo.list_lab_results(db_session, result.profile_id)
    assert len(labs) == 6
    assert any(r.abnormal_flag for r in labs)

    body_comp = clinical_repo.list_body_composition(db_session, result.profile_id)
    assert len(body_comp) == 1

    plans = planning_repo.list_plans(db_session, result.profile_id)
    assert len(plans) == 1
    sessions = planning_repo.list_sessions_for_plan(db_session, plans[0].id)
    assert {s.completion_status for s in sessions} == {"completed", "partial"}

    decisions = planning_repo.list_decision_log(db_session, result.profile_id)
    assert len(decisions) == 4

    config = profile_repo.get_config(db_session, result.profile_id)
    assert config.race_name == "Half marathon"
    assert config.weather_lat is not None
