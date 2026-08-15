"""Sophie — Streamlit entry point. This is the ONLY layer allowed to import
streamlit (see docs/ARCHITECTURE.md); all business logic lives in
sophie.services/domain/repositories/providers."""

from __future__ import annotations

import streamlit as st

from sophie.config import get_settings
from sophie.db import base as db_base
from sophie.repositories import profile_repo
from sophie.ui.streamlit.db_bootstrap import bootstrap_database
from sophie.ui.streamlit.errors import safe_action
from sophie.ui.streamlit.pages import (
    decision_log_page,
    health_page,
    memory_page,
    sunday_review_page,
)

st.set_page_config(page_title="Sophie", page_icon="🏃", layout="wide")


@st.cache_resource
def _startup() -> bool:
    bootstrap_database()
    return True


_startup()

with db_base.session_scope() as _session:
    _profile = profile_repo.get_or_create_profile(_session)
    _profile_id = _profile.id

st.sidebar.title("🏃 Sophie")
settings = get_settings()
if settings.sophie_demo_mode:
    st.sidebar.warning("Demo Mode is ON — all data shown is synthetic.")
    if st.sidebar.button("(Re)generate demo data"):
        with safe_action("Could not generate demo data"):
            from sophie.services.demo_data import seed_demo_data

            with db_base.session_scope() as demo_session:
                seed_demo_data(demo_session)
            st.sidebar.success("Demo data generated.")

page = st.sidebar.radio("Navigate", ["Sunday Review", "Health", "Memory / Config", "Decision Log"])

if page == "Sunday Review":
    sunday_review_page.render(_profile_id)
elif page == "Health":
    health_page.render(_profile_id)
elif page == "Memory / Config":
    memory_page.render(_profile_id)
elif page == "Decision Log":
    decision_log_page.render(_profile_id)
