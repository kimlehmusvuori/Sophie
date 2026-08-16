"""Memory / Config page — edit goals, planning/nutrition preferences, data
sources, family history, explicit exclusions, and free-text Sophie memory.
See docs/PRODUCT_SPEC.md §53-54."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from sophie.config import get_settings
from sophie.db import base as db_base
from sophie.repositories import import_repo
from sophie.services import (
    apple_health_import,
    clinical_import,
    export_service,
    memory_service,
    sports_tracker_import,
)
from sophie.ui.streamlit.errors import safe_action


def _resolve_source(uploaded: Any, local_path: str, suffix: str) -> Path | None:
    """Either writes an uploaded file's bytes to a temp file (cleaned up by
    the caller) or uses a local path the user typed directly — Sophie is
    local-first, so pointing at a path avoids uploading large files (e.g. a
    multi-hundred-MB Apple Health export) through the browser at all."""

    if uploaded is not None:
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(uploaded.getvalue())
        tmp.close()
        return Path(tmp.name)
    if local_path:
        path = Path(local_path).expanduser()
        if not path.exists():
            st.error(f"No file found at: {path}")
            return None
        return path
    st.warning("Provide a local file path or upload a file first.")
    return None


def _report_import_state(state: str, warnings: list[str] | None, error_summary: str | None) -> None:
    if state == "success":
        st.success("Import completed.")
    elif state == "partial":
        st.warning("Import completed with warnings.")
    elif state == "skipped_duplicate":
        st.info("This file was already imported — nothing new to add.")
    elif state == "failed":
        st.error(error_summary or "Import failed.")
    for warning in warnings or []:
        st.caption(f"⚠️ {warning}")


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

        st.subheader("Data imports")
        st.caption(
            "Point Sophie at a local file, or upload one. Raw files are never retained after "
            "processing — see docs/PRIVACY.md."
        )
        tab_ah, tab_st, tab_lab, tab_bc = st.tabs(
            ["Apple Health", "Sports Tracker", "Lab results", "Body composition"]
        )

        with tab_ah:
            ah_path = st.text_input("Local path to Apple Health export .zip", key="ah_path")
            ah_upload = st.file_uploader("...or upload the .zip", type=["zip"], key="ah_upload")
            if st.button("Import Apple Health", key="import_ah"):
                with safe_action("Apple Health import failed"):
                    source = _resolve_source(ah_upload, ah_path, ".zip")
                    if source is not None:
                        ah_result = apple_health_import.import_apple_health_zip(
                            session, profile_id, source
                        )
                        if ah_upload is not None:
                            source.unlink(missing_ok=True)
                        _report_import_state(
                            ah_result.state, ah_result.warnings, ah_result.error_summary
                        )
                        if ah_result.state != "failed":
                            st.write(
                                f"Workouts: {ah_result.workouts_created} new, "
                                f"{ah_result.workouts_matched} matched to existing. "
                                f"Daily samples written: {ah_result.daily_samples_written}. "
                                f"Catalogue entries: {ah_result.catalog_entries_written}."
                            )

        with tab_st:
            st_path = st.text_input("Local path to Sports Tracker export .zip", key="st_path")
            st_upload = st.file_uploader("...or upload the .zip", type=["zip"], key="st_upload")
            if st.button("Import Sports Tracker", key="import_st"):
                with safe_action("Sports Tracker import failed"):
                    source = _resolve_source(st_upload, st_path, ".zip")
                    if source is not None:
                        st_result = sports_tracker_import.import_sports_tracker_zip_file(
                            session, profile_id, source
                        )
                        if st_upload is not None:
                            source.unlink(missing_ok=True)
                        _report_import_state(
                            st_result.state, st_result.warnings, st_result.error_summary
                        )
                        if st_result.state != "failed":
                            st.write(
                                f"Workouts: {st_result.workouts_created} new, "
                                f"{st_result.workouts_matched} matched to existing."
                            )

        with tab_lab:
            provider_name = st.text_input("Lab provider name (free text)", key="lab_provider")
            lab_path = st.text_input(
                "Local path to a lab results file (.csv/.json/.pdf)", key="lab_path"
            )
            lab_upload = st.file_uploader(
                "...or upload one", type=["csv", "json", "pdf"], key="lab_upload"
            )
            if st.button("Import lab results", key="import_lab"):
                with safe_action("Lab result import failed"):
                    suffix = (
                        Path(lab_upload.name).suffix
                        if lab_upload is not None
                        else Path(lab_path or "").suffix
                    )
                    source = _resolve_source(lab_upload, lab_path, suffix or ".csv")
                    if source is not None:
                        response = clinical_import.import_lab_result_file(
                            session, profile_id, source, provider_name or None
                        )
                        if lab_upload is not None:
                            source.unlink(missing_ok=True)
                        if response.persisted:
                            st.success(f"Imported {len(response.outcome.results)} lab result(s).")
                        elif response.outcome.requires_confirmation:
                            st.session_state["pending_lab_results"] = response.outcome.results
                            st.session_state["pending_lab_provider"] = provider_name or None
                        for warning in response.outcome.warnings:
                            st.warning(warning)

            pending = st.session_state.get("pending_lab_results")
            if pending:
                st.write(
                    "**Review before saving** — PDF extraction is uncertain, confirm each value:"
                )
                for result in pending:
                    st.write(
                        f"{result.sample_date}: {result.test_name} = "
                        f"{result.value or result.value_text} {result.unit or ''} "
                        f"(ref: {result.reference_text or 'n/a'})"
                    )
                if st.button("Confirm and save these results", key="confirm_lab"):
                    with safe_action("Could not save confirmed results"):
                        clinical_import.confirm_and_persist_lab_results(
                            session,
                            profile_id,
                            st.session_state.get("pending_lab_provider"),
                            pending,
                        )
                        del st.session_state["pending_lab_results"]
                        st.success("Confirmed results saved.")
                        st.rerun()
                if st.button("Discard", key="discard_lab"):
                    del st.session_state["pending_lab_results"]
                    st.rerun()

        with tab_bc:
            bc_path = st.text_input(
                "Local path to a body composition file (.csv/.json)", key="bc_path"
            )
            bc_upload = st.file_uploader("...or upload one", type=["csv", "json"], key="bc_upload")
            if st.button("Import body composition", key="import_bc"):
                with safe_action("Body composition import failed"):
                    suffix = (
                        Path(bc_upload.name).suffix
                        if bc_upload is not None
                        else Path(bc_path or "").suffix
                    )
                    source = _resolve_source(bc_upload, bc_path, suffix or ".csv")
                    if source is not None:
                        assessments = clinical_import.import_body_composition_file(
                            session, profile_id, source
                        )
                        if bc_upload is not None:
                            source.unlink(missing_ok=True)
                        st.success(f"Imported {len(assessments)} body composition assessment(s).")

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
