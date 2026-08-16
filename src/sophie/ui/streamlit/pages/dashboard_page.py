"""Trends dashboard — one simple chart + trailing average per area (training,
sleep, weight, resting heart rate, HRV/recovery), toggled between Week/Month/
Year views. Deliberately literal, separate numbers — no composite score (see
docs/HEALTH_LOGIC_AND_SAFETY.md). UI only; aggregation lives in
sophie.services.dashboard_service.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sophie.services import dashboard_service
from sophie.ui.streamlit.errors import safe_action


def _render_metric(series: dashboard_service.MetricSeries) -> None:
    st.subheader(series.label)

    if series.days_with_data == 0:
        st.info("No data yet for this window.")
        return

    df = pd.DataFrame(
        {"value": [p.value for p in series.points]},
        index=pd.DatetimeIndex([p.day for p in series.points], name="date"),
    )
    st.line_chart(df, y="value", height=200)
    st.caption(
        f"Average: **{series.average} {series.unit}** "
        f"(data on {series.days_with_data} of {series.window_days} days)"
    )


def render(profile_id: str) -> None:
    st.header("Trends")
    st.caption(
        "One simple view per area, with the average for whichever window you pick. Each metric "
        "stays separate — Sophie never combines these into a single score."
    )

    timeframe = st.radio(
        "View",
        list(dashboard_service.TIMEFRAMES.keys()),
        horizontal=True,
        key="dashboard_timeframe",
    )

    from sophie.db import base as db_base

    with db_base.session_scope() as session:
        with safe_action("Could not compute trends"):
            series_list = dashboard_service.get_all_metric_series(session, profile_id, timeframe)

    if not series_list:
        return

    col1, col2 = st.columns(2)
    for i, series in enumerate(series_list):
        with col1 if i % 2 == 0 else col2:
            _render_metric(series)
