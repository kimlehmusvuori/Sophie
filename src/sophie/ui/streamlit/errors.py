"""User-facing error display. Never shows a raw traceback — see
docs/PRODUCT_SPEC.md §66."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import streamlit as st


@contextmanager
def safe_action(user_facing_summary: str) -> Iterator[None]:
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - last line of defense before the UI
        st.error(f"{user_facing_summary}: {exc}" if str(exc) else user_facing_summary)
