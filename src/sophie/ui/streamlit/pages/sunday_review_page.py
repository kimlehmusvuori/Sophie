"""Sunday Review page — the primary weekly workflow. See
docs/PRODUCT_SPEC.md §45 Steps A-H."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from sophie.config import get_settings
from sophie.db import base as db_base
from sophie.domain.planner import week_start_for
from sophie.domain.wellbeing import WHO5_QUESTIONS, WHO5_SCALE, score_who5
from sophie.providers.llm.openai_provider import OpenAICoachProvider
from sophie.providers.weather.open_meteo import OpenMeteoProvider
from sophie.repositories import health_intel_repo, planning_repo, profile_repo
from sophie.services import (
    calendar_context,
    data_status,
    health_intelligence,
    plan_vs_actual,
    sunday_review,
    weather_service,
)
from sophie.services import (
    coach as coach_service,
)
from sophie.ui.streamlit.errors import safe_action

_STATUS_ICON = {
    "completed": "✅",
    "partial": "🟡",
    "moved": "↔️",
    "missed": "❌",
    "ambiguous": "❓",
}


def render(profile_id: str) -> None:
    st.header("Sunday Review")
    settings = get_settings()
    today = date.today()
    week_start = week_start_for(today)
    st.caption(f"Planning week starting {week_start}")

    with db_base.session_scope() as session:
        config = profile_repo.get_config(session, profile_id)

        st.subheader("Step A — Data status")
        for s in data_status.get_data_status(session, profile_id, settings):
            detail = f" — {s.detail}" if s.detail else ""
            st.write(f"**{s.name}**: {s.status}{detail}")

        st.subheader("Step B — Last week")
        last_week = sunday_review.summarize_last_week(session, profile_id, week_start)
        col1, col2 = st.columns(2)
        col1.metric("Planned distance", f"{last_week.planned_km or 0:.1f} km")
        col2.metric("Actual distance", f"{last_week.actual_km or 0:.1f} km")
        st.write(last_week.completion_note or "No prior plan on file.")

        prior_plan = planning_repo.get_plan_for_week(
            session, profile_id, week_start - timedelta(days=7)
        )
        if prior_plan is not None:
            with safe_action("Could not compute plan-vs-actual"):
                pva = plan_vs_actual.match_plan_to_actuals(session, prior_plan.id, profile_id)
                sessions_by_id = {
                    s.id: s for s in planning_repo.list_sessions_for_plan(session, prior_plan.id)
                }
                for match in pva.session_results:
                    planned_session = sessions_by_id.get(match.session_id)
                    if planned_session is None:
                        continue
                    icon = _STATUS_ICON.get(match.status, "⚪")
                    st.write(
                        f"{icon} {planned_session.date} — {planned_session.session_type}: "
                        f"**{match.status}**"
                    )
                if pva.extra_unplanned_workout_ids:
                    st.caption(
                        f"{len(pva.extra_unplanned_workout_ids)} extra unplanned workout(s) logged."
                    )

        snapshot = health_intelligence.refresh_all_health_intelligence(session, profile_id, today)
        col1, col2 = st.columns(2)
        col1.write(f"Training load: **{snapshot.training_load.status}**")
        col2.write(f"Recovery: **{snapshot.recovery.status}**")

        st.subheader("Step C — Check-in")
        existing_checkin = planning_repo.get_checkin(session, profile_id, week_start)
        with st.form("checkin_form"):
            pain = st.slider(
                "Pain (0-10)", 0, 10, existing_checkin.pain_0_10 if existing_checkin else 0
            )
            pain_location = st.text_input(
                "Pain location (optional)",
                value=(existing_checkin.pain_location if existing_checkin else "") or "",
            )
            stress = st.slider(
                "Stress / mental load (1-5)",
                1,
                5,
                existing_checkin.stress_1_5 if existing_checkin else 2,
            )
            fasting = st.selectbox(
                "Fasting",
                ["good", "mixed", "poor"],
                index=["good", "mixed", "poor"].index(existing_checkin.fasting_quality)
                if existing_checkin and existing_checkin.fasting_quality
                else 0,
            )
            note = st.text_area(
                "Weekly note (optional)",
                value=(existing_checkin.note if existing_checkin else "") or "",
            )
            if st.form_submit_button("Save check-in"):
                with safe_action("Could not save check-in"):
                    sunday_review.record_manual_checkin(
                        session,
                        profile_id,
                        week_start,
                        pain,
                        pain_location or None,
                        stress,
                        fasting,
                        None,
                        None,
                        note or None,
                    )
                    st.success("Check-in saved.")

        st.subheader("Step D — Wellbeing")
        wb_status = health_intelligence.wellbeing_status(session, profile_id, today)
        if wb_status.get("due"):
            with st.form("who5_form"):
                st.caption("WHO-5 Well-Being Index — takes under a minute.")
                answers = [
                    st.select_slider(
                        q,
                        options=list(range(6)),
                        format_func=lambda i: WHO5_SCALE[i],
                        key=f"who5_{i}",
                    )
                    for i, q in enumerate(WHO5_QUESTIONS)
                ]
                if st.form_submit_button("Submit WHO-5"):
                    with safe_action("Could not save WHO-5"):
                        who5_result = score_who5(list(answers))
                        health_intel_repo.add_wellbeing_assessment(
                            session,
                            profile_id=profile_id,
                            assessed_at=today,
                            instrument="WHO-5",
                            instrument_version="1998-who-euro",
                            raw_score=who5_result.raw_score,
                            percentage_score=who5_result.percentage_score,
                            answers=list(answers),
                        )
                        st.success(f"WHO-5 recorded: {who5_result.percentage_score}%")
        else:
            st.caption(
                f"Wellbeing trend: {wb_status.get('trend', 'insufficient_data')} — "
                "not due this week."
            )

        st.subheader("Step E — Next week")
        uploaded = st.file_uploader(
            "Optional: upload an .ics calendar export for next week", type=["ics"]
        )
        if uploaded is not None:
            with safe_action("Could not parse the uploaded calendar file"):
                calendar_context.save_ics_upload(
                    session,
                    profile_id,
                    week_start,
                    uploaded.read().decode("utf-8", errors="ignore"),
                )
                st.success("Calendar file loaded.")

        fetch_result = calendar_context.fetch_busy_intervals_for_week(
            session, profile_id, week_start, settings
        )
        st.caption(
            f"Calendar source: {fetch_result.source} "
            f"({len(fetch_result.busy_intervals)} busy blocks)"
        )

        if settings.weather_configured and st.button("Refresh weather for next week"):
            with safe_action("Could not fetch weather"):
                weather_service.refresh_weather_for_range(
                    session,
                    profile_id,
                    OpenMeteoProvider(),
                    week_start,
                    week_start + timedelta(days=6),
                )
                st.success("Weather refreshed.")

        windows, rejected = calendar_context.build_calendar_windows(
            session,
            profile_id,
            week_start,
            config,
            snapshot.training_load.status,
            snapshot.recovery.status,
            fetch_result.busy_intervals,
        )
        top_windows = sorted(windows, key=lambda w: w.rank_score, reverse=True)[:5]
        for w in top_windows:
            st.write(
                f"- {w.weekday_name} {w.date} {w.start.strftime('%H:%M')} "
                f"(score {w.rank_score:.2f})"
            )
        if not top_windows:
            st.warning("No feasible training windows found for next week.")

        st.subheader("Step F — Sophie's recommendation")
        if st.button("Get Sophie's recommendation"):
            with safe_action("Could not generate a recommendation"):
                context = sunday_review.build_coach_context(
                    session, profile_id, week_start, windows, rejected, today
                )
                llm_provider = (
                    OpenAICoachProvider(
                        api_key=settings.openai_api_key or "", model=settings.openai_model
                    )
                    if settings.llm_configured
                    else None
                )
                result = coach_service.get_coach_recommendation(
                    context, llm_provider, prior_completion_ratio=last_week.completion_ratio
                )
                st.session_state["sophie_draft_recommendation"] = result
                st.session_state["sophie_draft_week_start"] = week_start

        draft = st.session_state.get("sophie_draft_recommendation")
        if draft is not None and st.session_state.get("sophie_draft_week_start") == week_start:
            rec = draft.recommendation
            source_label = "LLM-assisted" if draft.llm_used else "deterministic"
            st.write(f"**Verdict: {rec.verdict}** ({source_label})")
            for reason in rec.reasons:
                st.write(f"- {reason}")
            st.write("**Recommended plan:**")
            for s in rec.recommended_plan:
                st.write(
                    f"- {s.date} {s.start_time or ''} — {s.session_type}: {s.purpose}"
                    + (f" ({s.distance_km} km)" if s.distance_km else "")
                )
            st.write(f"**Conservative alternative:** {rec.conservative_alternative.summary}")
            if rec.coach_note:
                st.caption(rec.coach_note)

            st.subheader("Step G — Approve / modify")
            col1, col2 = st.columns(2)
            if col1.button("Approve as recommended"):
                with safe_action("Could not save the plan"):
                    plan = sunday_review.create_plan_from_recommendation(
                        session, profile_id, week_start, rec, draft.llm_used, draft.validation_notes
                    )
                    sunday_review.approve_plan(session, plan.id, modified=False)
                    st.session_state["sophie_approved_plan_id"] = plan.id
                    st.success("Plan approved.")
            if col2.button("Use conservative alternative instead"):
                with safe_action("Could not save the plan"):
                    from sophie.domain.coach_types import CoachRecommendation

                    alt_rec = CoachRecommendation(
                        verdict=rec.verdict,
                        reasons=rec.reasons,
                        recommended_plan=rec.conservative_alternative.sessions,
                        conservative_alternative=rec.conservative_alternative,
                        coach_note="User selected the conservative alternative.",
                    )
                    plan = sunday_review.create_plan_from_recommendation(
                        session,
                        profile_id,
                        week_start,
                        alt_rec,
                        draft.llm_used,
                        draft.validation_notes,
                    )
                    sunday_review.approve_plan(session, plan.id, modified=True)
                    st.session_state["sophie_approved_plan_id"] = plan.id
                    st.success("Conservative plan approved.")

        approved_plan_id = st.session_state.get("sophie_approved_plan_id")
        if approved_plan_id is not None:
            st.subheader("Step H — Final confirmation")
            graph_client = calendar_context.build_graph_client(settings)
            if graph_client.connection_status() == "connected":
                if st.button("Write to Outlook and save decision"):
                    with safe_action("Could not write to Outlook"):
                        writer = calendar_context.GraphEventWriter(graph_client)
                        count = sunday_review.write_plan_to_calendar(
                            session, approved_plan_id, writer
                        )
                        sunday_review.finalize_week_decision(
                            session,
                            profile_id,
                            week_start,
                            approved_plan_id,
                            f"{count} sessions written",
                        )
                        st.success(f"Wrote {count} events to Outlook and saved the decision.")
                        del st.session_state["sophie_approved_plan_id"]
            else:
                st.info(
                    "Outlook not connected — plan saved locally only (see docs/OUTLOOK_SETUP.md)."
                )
                if st.button("Save decision without writing to Outlook"):
                    with safe_action("Could not save the decision"):
                        sunday_review.finalize_week_decision(
                            session, profile_id, week_start, approved_plan_id
                        )
                        st.success("Decision saved.")
                        del st.session_state["sophie_approved_plan_id"]
