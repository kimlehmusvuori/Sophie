"""Health page — one consolidated page, separate legible domains, no
composite score. See docs/PRODUCT_SPEC.md §55 and docs/HEALTH_LOGIC_AND_SAFETY.md.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from sophie.repositories import clinical_repo
from sophie.services import health_intelligence
from sophie.ui.streamlit.errors import safe_action

_STATUS_BADGE = {
    "low": "🟢",
    "typical": "🟢",
    "normal": "🟢",
    "improving": "🟢",
    "stable": "🟡",
    "watch": "🟡",
    "at_baseline": "🟢",
    "below_baseline": "🟡",
    "above_baseline": "🟢",
    "elevated": "🟠",
    "concern": "🔴",
    "very_elevated": "🔴",
    "declining": "🔴",
    "insufficient_data": "⚪",
}


def _badge(status: str) -> str:
    return _STATUS_BADGE.get(status, "⚪")


def render(profile_id: str) -> None:
    st.header("Health")
    st.caption(
        "Separate, honest health domains — trend + evidence + data quality. "
        "Sophie never combines these into a single score."
    )

    from sophie.db import base as db_base

    with db_base.session_scope() as session:
        with safe_action("Could not compute health intelligence"):
            snapshot = health_intelligence.refresh_all_health_intelligence(
                session, profile_id, date.today()
            )
        lab_results = clinical_repo.list_lab_results(session, profile_id)
        body_comp = clinical_repo.list_body_composition(session, profile_id)

    if snapshot is None:
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"{_badge(snapshot.cardio_trend.overall_trend)} Cardiovascular / metabolic")
        st.write(
            f"Trend: **{snapshot.cardio_trend.overall_trend}** "
            f"(data quality: {snapshot.cardio_trend.data_quality})"
        )
        st.json(snapshot.cardio_trend.evidence, expanded=False)

        st.subheader(f"{_badge(snapshot.training_load.status)} Training capacity / load")
        st.write(
            f"Status: **{snapshot.training_load.status}** "
            f"(data quality: {snapshot.training_load.data_quality})"
        )
        st.json(snapshot.training_load.evidence, expanded=False)

        st.subheader(f"{_badge(snapshot.recovery.status)} Recovery")
        st.write(
            f"Status: **{snapshot.recovery.status}** "
            f"(data quality: {snapshot.recovery.data_quality})"
        )
        st.json(snapshot.recovery.signals, expanded=False)

        st.subheader(f"{_badge(snapshot.aerobic_efficiency_trend.trend)} Aerobic efficiency proxy")
        st.write(
            f"Trend: **{snapshot.aerobic_efficiency_trend.trend}** "
            f"(data quality: {snapshot.aerobic_efficiency_trend.data_quality})"
        )

    with col2:
        st.subheader(f"{_badge(snapshot.circadian.data_quality)} Sleep / circadian")
        st.write(f"Data quality: **{snapshot.circadian.data_quality}**")
        st.write(f"Bedtime variability: {snapshot.circadian.bedtime_variability_min} min")
        st.write(f"Disrupted nights: {snapshot.circadian.disrupted_nights}")
        st.write(f"Avg daylight: {snapshot.circadian.avg_daylight_minutes} min")

        wellbeing = snapshot.wellbeing
        st.subheader("🧠 Mental wellbeing (WHO-5)")
        st.write(f"Trend: **{wellbeing.get('trend', 'insufficient_data')}**")
        st.write(f"Latest score: {wellbeing.get('latest_percentage', 'n/a')}")
        if wellbeing.get("due"):
            st.info("A WHO-5 check-in is due — it will appear in your next Sunday Review.")

        st.subheader(f"{_badge(snapshot.movement.status)} Everyday movement")
        st.write(f"Status: **{snapshot.movement.status}** vs your personal baseline")
        st.write(
            f"Avg daily steps: {snapshot.movement.avg_daily_steps} "
            f"(baseline: {snapshot.movement.personal_baseline_steps})"
        )

        st.subheader("👂 Hearing / noise exposure")
        st.write(f"Data quality: **{snapshot.hearing.data_quality}**")
        st.write(f"Headphone avg: {snapshot.hearing.headphone_avg_db} dB")
        st.write(f"Environmental avg: {snapshot.hearing.environmental_avg_db} dB")
        st.caption("Reflects exposure only — not a hearing-loss diagnosis.")

    st.divider()
    st.subheader("🧪 Clinical / laboratory")
    if not lab_results:
        st.info("No lab results imported yet.")
    else:
        by_category: dict[str, list] = {}
        for r in lab_results:
            by_category.setdefault(r.category, []).append(r)
        for category, results in sorted(by_category.items()):
            with st.expander(f"{category} ({len(results)})"):
                for r in sorted(results, key=lambda x: x.sample_date):
                    flag = f" [{r.abnormal_flag}]" if r.abnormal_flag else ""
                    ref = r.reference_text or (
                        f"{r.reference_low}-{r.reference_high}"
                        if r.reference_low is not None
                        else "n/a"
                    )
                    st.write(
                        f"{r.sample_date}: **{r.test_name}** = {r.value or r.value_text} "
                        f"{r.unit or ''}{flag} (ref: {ref})"
                    )

    st.subheader("⚖️ Body composition")
    if not body_comp:
        st.info("No body composition assessments imported yet.")
    else:
        for assessment in sorted(body_comp, key=lambda a: a.assessed_at):
            st.write(
                f"{assessment.assessed_at} ({assessment.method}): weight {assessment.weight_kg}kg, "
                f"body fat {assessment.body_fat_pct}%, lean mass {assessment.lean_mass_kg}kg"
            )
        st.caption(
            "Method shown alongside each measurement — different methods are not directly "
            "comparable."
        )
