from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "sophie"


def test_streamlit_only_imported_under_ui_streamlit():
    offenders = []
    for path in SRC.rglob("*.py"):
        if "ui/streamlit" in str(path.relative_to(SRC)).replace("\\", "/"):
            continue
        text = path.read_text(encoding="utf-8")
        if "import streamlit" in text or "from streamlit" in text:
            offenders.append(str(path.relative_to(SRC)))
    assert offenders == [], f"streamlit imported outside ui/streamlit: {offenders}"


def test_domain_layer_has_no_sqlalchemy_or_http_imports():
    domain_dir = SRC / "domain"
    offenders = []
    forbidden = ("sqlalchemy", "httpx", "streamlit", "msal")
    for path in domain_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if f"import {token}" in text or f"from {token}" in text:
                offenders.append((str(path.relative_to(SRC)), token))
    assert offenders == [], f"domain layer has forbidden imports: {offenders}"
