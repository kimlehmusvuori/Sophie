"""Memory / Config page — edit goals, planning/nutrition preferences, data
sources, family history, explicit exclusions, and free-text Sophie memory.
See docs/PRODUCT_SPEC.md §53-54."""

from __future__ import annotations

import streamlit as st

from sophie.config import get_settings
from sophie.db import base as db_base
from sophie.repositories import import_repo
from sophie.services import export_service, memory_service
from sophie.ui.streamlit.errors import safe_action


def render(profile_id: str) -> None:
    st.header("Memory / Config")

    with db_base.session_scope() as session:
        snapshot = memory_service.get_memory_snapshot(session, profile_id)
        config = snapshot.config

        st.subheader("Goals")
        col1, col2 = st.columns(2)
        with col1:
            race_name = st.text_input("Race name", value=config.race_name or "")
            race_date = st.date_input("Race date", value=config.race_date)
        with col2:
            current_weight = st.number_input(
                "Current weight (kg)", value=float(config.current_weight_kg or 90.0), step=0.1
            )
            weight_goal = st.number_input(
                "Weight goal (kg)", value=float(config.weight_goal_kg or 79.0), step=0.1
            )
        if st.button("Save goals"):
            with safe_action("Could not save goals"):
                memory_service.update_goals(
                    session, profile_id, race_name, race_date, weight_goal, current_weight
                )
                st.success("Goals saved.")

        st.subheader("Planning preferences")
        col1, col2, col3 = st.columns(3)
        with col1:
            max_runs = st.number_input(
                "Max runs per week", min_value=0, max_value=3, value=config.max_runs_per_week
            )
        with col2:
            padel_weekday = st.selectbox(
                "Padel weekday",
                options=list(range(7)),
                index=config.padel_weekday if config.padel_weekday is not None else 3,
                format_func=lambda i: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i],
            )
        with col3:
            preserve_rest_day = st.checkbox("Preserve one rest day", value=config.preserve_rest_day)
        if st.button("Save planning preferences"):
            with safe_action("Could not save planning preferences"):
                memory_service.update_planning_preferences(
                    session,
                    profile_id,
                    max_runs_per_week=int(max_runs),
                    padel_weekday=int(padel_weekday),
                    preserve_rest_day=preserve_rest_day,
                )
                st.success("Planning preferences saved.")

        st.subheader("Nutrition preferences")
        col1, col2 = st.columns(2)
        with col1:
            gluten_free = st.checkbox("Gluten-free", value=config.gluten_free)
        with col2:
            paleo_inspired = st.checkbox("Paleo-inspired", value=config.paleo_inspired)
        fasting_window = st.text_input("Fasting window", value=config.fasting_window or "")
        if st.button("Save nutrition preferences"):
            with safe_action("Could not save nutrition preferences"):
                memory_service.update_nutrition_preferences(
                    session,
                    profile_id,
                    gluten_free=gluten_free,
                    paleo_inspired=paleo_inspired,
                    fasting_window=fasting_window or None,
                )
                st.success("Nutrition preferences saved.")

        st.subheader("Weather / data sources")
        settings = get_settings()
        col1, col2, col3 = st.columns(3)
        with col1:
            location_name = st.text_input("Location name", value=config.weather_location_name or "")
        with col2:
            lat = st.number_input(
                "Latitude",
                value=float(config.weather_lat) if config.weather_lat else 0.0,
                format="%.4f",
            )
        with col3:
            lon = st.number_input(
                "Longitude",
                value=float(config.weather_lon) if config.weather_lon else 0.0,
                format="%.4f",
            )
        if st.button("Save location"):
            with safe_action("Could not save location"):
                memory_service.update_weather_location(
                    session, profile_id, location_name or None, lat, lon
                )
                st.success("Location saved.")

        st.caption(
            f"Outlook: {'configured' if settings.calendar_configured else 'not configured'} — "
            f"see docs/OUTLOOK_SETUP.md. LLM: "
            f"{'configured' if settings.llm_configured else 'not configured'} "
            "(deterministic-only planning if unconfigured)."
        )

        st.subheader("Family history (optional, private, context-only)")
        st.caption(
            "This is context only — Sophie never uses it to diagnose disease. "
            "See docs/HEALTH_LOGIC_AND_SAFETY.md."
        )
        for item in snapshot.family_history:
            col1, col2 = st.columns([5, 1])
            col1.write(f"**{item.category}** — {item.note or ''}")
            if col2.button("Remove", key=f"remove_fh_{item.id}"):
                with safe_action("Could not remove item"):
                    memory_service.remove_family_history(session, item.id)
                    st.rerun()

        with st.form("add_family_history"):
            category = st.selectbox(
                "Category", ["cardiovascular", "diabetes", "autoimmune_inflammatory", "other"]
            )
            note = st.text_input("Note (optional)")
            if st.form_submit_button("Add"):
                with safe_action("Could not add family history item"):
                    memory_service.add_family_history(session, profile_id, category, note or None)
                    st.rerun()

        st.subheader("Sophie memory (free text, edited by you only)")
        st.caption(
            "Sophie's coach suggestions never automatically become permanent memory — "
            "only what you explicitly save here."
        )
        memory_text = st.text_area("Notes for Sophie", value=config.sophie_memory or "", height=120)
        if st.button("Save memory"):
            with safe_action("Could not save memory"):
                memory_service.update_sophie_memory(session, profile_id, memory_text or None)
                st.success("Memory saved.")

        with st.expander("Apple Health data status — full metric catalogue"):
            catalog = import_repo.list_metric_catalog(session, profile_id)
            if not catalog:
                st.caption("No Apple Health import yet.")
            else:
                st.caption(
                    "Every Apple Health record type seen, whether Sophie currently uses it, "
                    "and the date range/approximate count — see docs/PRODUCT_SPEC.md §10."
                )
                for entry in sorted(catalog, key=lambda e: e.record_type):
                    st.write(
                        f"**{entry.friendly_name}** ({entry.record_type}) — {entry.status}, "
                        f"~{entry.approx_record_count} records"
                        + (
                            f", {entry.first_seen_at.date()} to {entry.last_seen_at.date()}"
                            if entry.first_seen_at and entry.last_seen_at
                            else ""
                        )
                    )

        with st.expander("Export processed data"):
            st.caption("JSON/CSV export of everything Sophie has derived — never raw source files.")
            with safe_action("Could not export data"):
                json_data = export_service.export_profile_json(session, profile_id)
                st.download_button(
                    "Download JSON export", json_data, file_name="sophie_export.json"
                )
                csv_data = export_service.export_workouts_csv(session, profile_id)
                st.download_button(
                    "Download workouts CSV", csv_data, file_name="sophie_workouts.csv"
                )
