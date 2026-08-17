"""Mail Docket — review unanswered work threads and send the replies.

Run with:  streamlit run mailops/app.py

Each dossier shows why the thread was flagged, what the counterpart actually
asked, and an editable draft. Sending is two taps: Send reply, then Confirm.
Nothing leaves the mailbox without that confirmation.
"""

from __future__ import annotations

import streamlit as st
from docket_data import DOSSIERS, Dossier
from graph_client import (
    GraphError,
    acquire_token_silent,
    begin_device_flow,
    build_app,
    complete_device_flow,
    load_config,
    send_mail,
    signed_in_as,
)

SEVERITY_LABEL = {
    "urgent": ("Reply today", "#a5382a"),
    "high": ("High priority", "#a5382a"),
    "medium": ("Needs an answer", "#946822"),
}

st.set_page_config(page_title="Mail Docket", page_icon="📮", layout="centered")


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
def _init_state() -> None:
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("account", None)
    st.session_state.setdefault("device_flow", None)
    st.session_state.setdefault("sent", {})  # key -> confirmation text
    st.session_state.setdefault("confirming", None)  # key awaiting confirmation
    st.session_state.setdefault("errors", {})  # key -> error text


_init_state()


@st.cache_resource(show_spinner=False)
def _msal_app():
    """One MSAL client for the process, sharing the on-disk token cache."""
    return build_app(load_config())


# --------------------------------------------------------------------------
# Sign-in
# --------------------------------------------------------------------------
def render_sign_in() -> bool:
    """Render sign-in state. Returns True when a usable token is held."""
    try:
        app = _msal_app()
    except GraphError as exc:
        st.error(str(exc))
        st.info(
            "The drafts below are still readable — only sending needs sign-in.",
            icon="ℹ️",
        )
        return False

    if st.session_state.token is None:
        token = acquire_token_silent(app)
        if token:
            st.session_state.token = token

    if st.session_state.token:
        if st.session_state.account is None:
            try:
                st.session_state.account = signed_in_as(st.session_state.token)
            except GraphError as exc:
                # Cached token is stale — force a fresh sign-in.
                st.session_state.token = None
                st.warning(str(exc))
                return False
        st.success(f"Signed in as {st.session_state.account}")
        return True

    st.info("Sign in to your Microsoft account to enable sending.")

    if st.session_state.device_flow is None:
        if st.button("Sign in", type="primary"):
            try:
                st.session_state.device_flow = begin_device_flow(app)
            except GraphError as exc:
                st.error(str(exc))
            st.rerun()
        return False

    flow = st.session_state.device_flow
    st.markdown(f"Open **{flow['verification_uri']}** and enter this code:")
    st.code(flow["user_code"], language=None)
    st.caption("Then come back here and press Continue.")

    columns = st.columns(2)
    if columns[0].button("Continue", type="primary"):
        with st.spinner("Waiting for Microsoft to confirm…"):
            try:
                st.session_state.token = complete_device_flow(app, flow)
                st.session_state.device_flow = None
            except GraphError as exc:
                st.error(str(exc))
        st.rerun()
    if columns[1].button("Cancel"):
        st.session_state.device_flow = None
        st.rerun()
    return False


# --------------------------------------------------------------------------
# Dossiers
# --------------------------------------------------------------------------
def render_dossier(item: Dossier, *, can_send: bool) -> None:
    label, colour = SEVERITY_LABEL.get(item.severity, ("Open", "#946822"))

    st.markdown(f"### {item.title}")
    st.markdown(
        f"<span style='color:{colour};font-weight:600;font-size:0.85rem'>{label}</span>"
        f" &nbsp;·&nbsp; <span style='color:#666;font-size:0.85rem'>{item.age}</span>",
        unsafe_allow_html=True,
    )
    st.caption(item.counterpart)
    st.markdown(f"**Why flagged:** {item.why}")

    with st.expander("What they wrote"):
        st.markdown(f"> {item.excerpt}")
        st.caption(item.excerpt_source)

    sent_note = st.session_state.sent.get(item.key)
    if sent_note:
        st.success(sent_note)
        st.divider()
        return

    body = st.text_area(
        "Draft reply — edit before sending",
        value=item.draft,
        key=f"body_{item.key}",
        height=190,
    )

    recipients = ", ".join(item.to)
    cc_line = f" · Cc {', '.join(item.cc)}" if item.cc else ""
    st.caption(f"To {recipients}{cc_line} · Subject: {item.subject}")

    if item.caution:
        st.warning(item.caution, icon="⚠️")

    error = st.session_state.errors.get(item.key)
    if error:
        st.error(error)

    if not can_send:
        st.button("Send reply", key=f"send_{item.key}", disabled=True)
        st.caption("Sign in above to enable sending.")
        st.divider()
        return

    if st.session_state.confirming == item.key:
        st.markdown("**Send this now?**")
        confirm_columns = st.columns(2)
        if confirm_columns[0].button("Confirm & send", key=f"confirm_{item.key}", type="primary"):
            _do_send(item, body)
            st.rerun()
        if confirm_columns[1].button("Cancel", key=f"cancel_{item.key}"):
            st.session_state.confirming = None
            st.rerun()
    else:
        if st.button("Send reply", key=f"send_{item.key}", type="primary"):
            st.session_state.confirming = item.key
            st.session_state.errors.pop(item.key, None)
            st.rerun()

    st.divider()


def _do_send(item: Dossier, body: str) -> None:
    """Send one reply, recording either a confirmation or the real error."""
    try:
        send_mail(
            st.session_state.token,
            to=item.to,
            cc=item.cc,
            subject=item.subject,
            body=body,
        )
    except GraphError as exc:
        # A timeout or 5xx leaves the outcome genuinely unknown — say so rather
        # than inviting a second send that might duplicate the first.
        if exc.status is None or exc.status >= 500:
            st.session_state.errors[item.key] = (
                f"{exc} — the outcome is unknown. Check Sent Items before trying again."
            )
        else:
            st.session_state.errors[item.key] = str(exc)
        st.session_state.confirming = None
        return
    except Exception as exc:  # network stack failures surface here
        st.session_state.errors[item.key] = (
            f"Could not reach Microsoft: {exc}. Check Sent Items before trying again."
        )
        st.session_state.confirming = None
        return

    st.session_state.sent[item.key] = f"Sent to {', '.join(item.to)} — a copy is in Sent Items."
    st.session_state.confirming = None


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
st.title("Mail Docket")
st.caption("Unanswered work threads, with the reply ready to send.")

can_send = render_sign_in()
st.divider()

open_items = [d for d in DOSSIERS if d.key not in st.session_state.sent]
st.markdown(f"**{len(open_items)} of {len(DOSSIERS)} still open**")
st.write("")

for dossier in DOSSIERS:
    render_dossier(dossier, can_send=can_send)

st.caption(
    "Replies are sent from your own Microsoft account via Graph and saved to Sent Items. "
    "Nothing is sent without pressing Confirm."
)
