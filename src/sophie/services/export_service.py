"""Export of Sophie-owned processed data. See docs/PRODUCT_SPEC.md §82 —
JSON (profile/config, metric catalogue, canonical workouts, health
summaries, wellbeing, lab data, body composition, plans, decision log) plus
CSV for tabular data. Never includes raw source files/tokens."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from sophie.repositories import (
    clinical_repo,
    health_intel_repo,
    import_repo,
    planning_repo,
    profile_repo,
    workout_repo,
)


def _row_to_dict(row: Any) -> dict[str, Any]:
    mapper = inspect(row).mapper
    result = {}
    for column in mapper.columns:
        value = getattr(row, column.key)
        if isinstance(value, datetime | date):
            value = value.isoformat()
        result[column.key] = value
    return result


def export_profile_json(session: Session, profile_id: str) -> str:
    profile = profile_repo.get_or_create_profile(session)
    config = profile_repo.get_config(session, profile_id)

    payload = {
        "profile": _row_to_dict(profile),
        "config": _row_to_dict(config),
        "family_history": [
            _row_to_dict(i) for i in profile_repo.list_family_history(session, profile_id)
        ],
        "apple_health_metric_catalog": [
            _row_to_dict(i) for i in import_repo.list_metric_catalog(session, profile_id)
        ],
        "canonical_workouts": [
            _row_to_dict(w) for w in workout_repo.list_workouts(session, profile_id)
        ],
        "wellbeing_assessments": [
            _row_to_dict(w)
            for w in health_intel_repo.list_wellbeing_assessments(session, profile_id)
        ],
        "lab_results": [
            _row_to_dict(r) for r in clinical_repo.list_lab_results(session, profile_id)
        ],
        "body_composition": [
            _row_to_dict(b) for b in clinical_repo.list_body_composition(session, profile_id)
        ],
        "plans": [
            _row_to_dict(p) for p in planning_repo.list_plans(session, profile_id, limit=1000)
        ],
        "decision_log": [
            _row_to_dict(d)
            for d in planning_repo.list_decision_log(session, profile_id, limit=1000)
        ],
    }
    return json.dumps(payload, indent=2, default=str)


def export_workouts_csv(session: Session, profile_id: str) -> str:
    workouts = workout_repo.list_workouts(session, profile_id)
    buffer = io.StringIO()
    fieldnames = [
        "id",
        "activity_type",
        "start_at",
        "end_at",
        "duration_s",
        "distance_m",
        "avg_hr",
        "max_hr",
        "elevation_gain_m",
        "avg_pace_s_per_km",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for w in workouts:
        writer.writerow({k: getattr(w, k) for k in fieldnames})
    return buffer.getvalue()
