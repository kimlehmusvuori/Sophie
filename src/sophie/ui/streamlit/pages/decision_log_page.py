"""Decision Log page — view-only. See docs/PRODUCT_SPEC.md §56."""

from __future__ import annotations

import streamlit as st

from sophie.db import base as db_base
from sophie.services import decision_log_service


def render(profile_id: str) -> None:
    st.header("Decision Log")
    st.caption("View-only weekly record of Sophie's recommendations and outcomes.")

    with db_base.session_scope() as session:
        entries = decision_log_service.list_decision_log(session, profile_id)

    if not entries:
        st.info("No decisions recorded yet — complete a Sunday Review to populate this log.")
        return

    for entry in sorted(entries, key=lambda e: e.week_start, reverse=True):
        with st.expander(f"Week of {entry.week_start} — verdict: {entry.verdict or 'n/a'}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Training load status:** {entry.training_load_status or 'n/a'}")
                st.write(f"**Data quality:** {entry.data_quality_summary or 'n/a'}")
                st.write(f"**Calendar write state:** {entry.calendar_write_state or 'n/a'}")
            with col2:
                st.write(f"**Actual result:** {entry.actual_result_summary or 'n/a'}")
                st.write(f"**Coach note:** {entry.coach_note or 'n/a'}")
