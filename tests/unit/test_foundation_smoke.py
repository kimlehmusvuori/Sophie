from __future__ import annotations

from sophie.repositories import profile_repo, workout_repo


def test_profile_and_config_created(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    assert profile.id
    config = profile_repo.get_config(db_session, profile.id)
    assert config.max_runs_per_week == 3

    same_profile = profile_repo.get_or_create_profile(db_session)
    assert same_profile.id == profile.id


def test_update_config(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    profile_repo.update_config(db_session, profile.id, weight_goal_kg=79.0)
    config = profile_repo.get_config(db_session, profile.id)
    assert config.weight_goal_kg == 79.0


def test_family_history_is_optional_and_editable(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    assert profile_repo.list_family_history(db_session, profile.id) == []
    item = profile_repo.add_family_history_item(
        db_session, profile.id, "cardiovascular", "context note"
    )
    assert len(profile_repo.list_family_history(db_session, profile.id)) == 1
    profile_repo.delete_family_history_item(db_session, item.id)
    assert profile_repo.list_family_history(db_session, profile.id) == []


def test_canonical_workout_dedup_match(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    import datetime as dt

    start_dt = dt.datetime(2026, 8, 1, 8, 0)
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="run",
        start_at=start_dt,
        duration_s=3600,
        distance_m=10000,
    )
    match = workout_repo.find_matching_workout(db_session, profile.id, "run", start_dt, 10050)
    assert match is not None

    no_match = workout_repo.find_matching_workout(
        db_session, profile.id, "run", start_dt + dt.timedelta(hours=5), 10000
    )
    assert no_match is None
