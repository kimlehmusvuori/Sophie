"""Chat page — free-form Q&A grounded in sanitized health/training summaries.
See docs/PRIVACY.md: only pre-computed domain statuses and trailing-window
averages ever reach the selected provider, never raw Apple Health/Sports
Tracker/clinical records. UI only; all logic lives in sophie.services.chat_service.
"""

from __future__ import annotations

import streamlit as st

from sophie.config import get_settings
from sophie.providers.llm import CHAT_PROVIDER_LABELS
from sophie.repositories import chat_repo, profile_repo
from sophie.services import chat_service
from sophie.ui.streamlit.errors import safe_action


def render(profile_id: str) -> None:
    st.header("Chat")
    st.caption(
        "Ask about your training, sleep, recovery, or other trends. Sophie only ever shares "
        "already-processed summaries with the provider you pick below — never your raw Apple "
        "Health, Sports Tracker, or clinical data. Not a substitute for medical advice."
    )

    from sophie.db import base as db_base

    settings = get_settings()

    with db_base.session_scope() as session:
        config = profile_repo.get_config(session, profile_id)
        current_provider = config.llm_chat_provider

    provider_keys = list(CHAT_PROVIDER_LABELS.keys())
    labels = [
        CHAT_PROVIDER_LABELS[key]
        + ("" if settings.chat_provider_configured(key) else " — not configured")
        for key in provider_keys
    ]
    selected_index = (
        provider_keys.index(current_provider) if current_provider in provider_keys else 0
    )
    chosen_label = st.selectbox(
        "Provider", labels, index=selected_index, key="chat_provider_select"
    )
    chosen_provider = provider_keys[labels.index(chosen_label)]

    if chosen_provider != current_provider:
        with db_base.session_scope() as session:
            profile_repo.update_config(session, profile_id, llm_chat_provider=chosen_provider)

    if not settings.chat_provider_configured(chosen_provider):
        st.info(
            f"{CHAT_PROVIDER_LABELS[chosen_provider]} isn't configured yet — add its API key in "
            "your .env file, then restart Sophie."
        )

    with db_base.session_scope() as session:
        history = chat_repo.list_messages(session, profile_id)

    for message in history:
        with st.chat_message(message.role):
            st.write(message.content)

    if st.button("Clear conversation", disabled=not history):
        with db_base.session_scope() as session:
            chat_repo.clear_messages(session, profile_id)
        st.rerun()

    question = st.chat_input("Ask Sophie about your training or health data...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner(f"Asking {CHAT_PROVIDER_LABELS[chosen_provider]}..."):
                with safe_action("Chat request failed"):
                    with db_base.session_scope() as session:
                        result = chat_service.ask(
                            session, profile_id, settings, chosen_provider, question
                        )
                    st.write(result.text)
        st.rerun()
