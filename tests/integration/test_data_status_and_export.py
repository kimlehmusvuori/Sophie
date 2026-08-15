from __future__ import annotations

import json
from datetime import date

from sophie.config.settings import Settings
from sophie.repositories import profile_repo
from sophie.services import data_status, export_service
from sophie.services.demo_data import seed_demo_data


def _settings(**overrides: object) -> Settings:
    base = dict(ms_graph_client_id=None, weather_lat=None, weather_lon=None, openai_api_key=None)
    base.update(overrides)
    return Settings(**base)


def test_data_status_reports_unconfigured_and_never_imported(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    statuses = data_status.get_data_status(db_session, profile.id, _settings())

    by_name = {s.name: s for s in statuses}
    assert by_name["Apple Health"].status == "never_imported"
    assert by_name["Outlook"].status == "not_configured"
    assert by_name["Weather"].status == "not_configured"
    assert by_name["LLM (OpenAI)"].status == "not_configured"
    assert by_name["Clinical/lab data"].status == "never_imported"


def test_data_status_reflects_configuration(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    statuses = data_status.get_data_status(
        db_session,
        profile.id,
        _settings(
            ms_graph_client_id="abc", weather_lat=60.1, weather_lon=24.9, openai_api_key="sk-x"
        ),
    )
    by_name = {s.name: s for s in statuses}
    assert by_name["Outlook"].status == "ok"
    assert by_name["Weather"].status == "ok"
    assert by_name["LLM (OpenAI)"].status == "ok"


def test_export_profile_json_contains_expected_sections(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    seed_demo_data(db_session, as_of=date(2026, 8, 15))

    payload = json.loads(export_service.export_profile_json(db_session, profile.id))

    for key in (
        "profile",
        "config",
        "family_history",
        "apple_health_metric_catalog",
        "canonical_workouts",
        "wellbeing_assessments",
        "lab_results",
        "body_composition",
        "plans",
        "decision_log",
    ):
        assert key in payload

    assert len(payload["canonical_workouts"]) > 0
    assert len(payload["lab_results"]) == 6
    assert payload["config"]["race_name"] == "Half marathon"
    # Never leaks a raw file path or token into the export.
    assert "token" not in json.dumps(payload).lower()


def test_export_workouts_csv_has_header_and_rows(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    seed_demo_data(db_session, as_of=date(2026, 8, 15))

    csv_text = export_service.export_workouts_csv(db_session, profile.id)
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("id,activity_type")
    assert len(lines) > 1
