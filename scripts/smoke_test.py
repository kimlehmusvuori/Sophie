#!/usr/bin/env python3
"""Local smoke test: exercises a full synthetic Sunday Review end to end
against a throwaway SQLite database, with no Streamlit, no network, and no
LLM required. Run this after any change to db/, services/, or providers/.

Usage:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sophie.config.settings import Settings  # noqa: E402
from sophie.db import base as db_base  # noqa: E402
from sophie.db.models import Base  # noqa: E402
from sophie.domain.planner import week_start_for  # noqa: E402
from sophie.repositories import profile_repo  # noqa: E402
from sophie.services import (  # noqa: E402
    calendar_context,
    coach,
    data_status,
    health_intelligence,
    sunday_review,  # noqa: E402
)
from sophie.services.demo_data import seed_demo_data  # noqa: E402

_SETTINGS = Settings(
    ms_graph_client_id=None, weather_lat=None, weather_lon=None, openai_api_key=None
)


def _check(label: str, condition: bool) -> None:
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(f"Smoke test failed at: {label}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="sophie_smoke_") as tmp_dir:
        db_path = Path(tmp_dir) / "smoke.db"
        db_base.configure(f"sqlite:///{db_path}")
        Base.metadata.create_all(db_base.get_engine())
        print(f"Database created at {db_path}")

        with db_base.session_scope() as session:
            profile = profile_repo.get_or_create_profile(session)
            _check("profile created", bool(profile.id))

            result = seed_demo_data(session, as_of=date.today())
            _check("demo data seeded", result.weeks_seeded == 8)

        today = date.today()
        week_start = week_start_for(today)

        with db_base.session_scope() as session:
            statuses = data_status.get_data_status(session, profile.id, _SETTINGS)
            _check("data status computed", len(statuses) >= 6)

            last_week = sunday_review.summarize_last_week(session, profile.id, week_start)
            _check("last week summarized", last_week.planned_km is not None)

            snapshot = health_intelligence.refresh_all_health_intelligence(
                session, profile.id, today
            )
            _check("health intelligence computed", snapshot.training_load.status is not None)

            config = profile_repo.get_config(session, profile.id)
            fetch_result = calendar_context.fetch_busy_intervals_for_week(
                session, profile.id, week_start, _SETTINGS
            )
            windows, rejected = calendar_context.build_calendar_windows(
                session,
                profile.id,
                week_start,
                config,
                snapshot.training_load.status,
                snapshot.recovery.status,
                fetch_result.busy_intervals,
            )
            _check("calendar windows computed", len(windows) > 0)

            context = sunday_review.build_coach_context(
                session, profile.id, week_start, windows, rejected, today
            )
            coach_result = coach.get_coach_recommendation(
                context, llm_provider=None, prior_completion_ratio=last_week.completion_ratio
            )
            _check("deterministic coach recommendation produced", coach_result.llm_used is False)
            _check(
                "recommendation respects max runs/week",
                len(coach_result.recommendation.recommended_plan) <= context.max_runs_per_week,
            )

            plan = sunday_review.create_plan_from_recommendation(
                session,
                profile.id,
                week_start,
                coach_result.recommendation,
                False,
                coach_result.validation_notes,
            )
            plan = sunday_review.approve_plan(session, plan.id, modified=False)
            _check("plan approved", plan.state == "approved")

            sunday_review.finalize_week_decision(
                session, profile.id, week_start, plan.id, "smoke test"
            )
            entries = sunday_review.decision_log_service.list_decision_log(session, profile.id)
            _check("decision recorded", len(entries) >= 1)

        print("\nAll smoke test checks passed.")


if __name__ == "__main__":
    main()
