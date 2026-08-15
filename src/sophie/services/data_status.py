"""Sunday Review Step A: concise data-source status. See
docs/PRODUCT_SPEC.md §45 Step A."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.config.settings import Settings
from sophie.db.models import ImportManifest
from sophie.repositories import clinical_repo


@dataclass
class SourceStatus:
    name: str
    configured: bool
    status: str  # not_configured/never_imported/ok/stale
    detail: str | None = None


def _last_successful_import(
    session: Session, profile_id: str, source_type: str
) -> ImportManifest | None:
    return session.execute(
        select(ImportManifest)
        .where(
            ImportManifest.profile_id == profile_id,
            ImportManifest.source_type == source_type,
            ImportManifest.state.in_(("success", "partial")),
        )
        .order_by(ImportManifest.finished_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _import_source_status(
    session: Session, profile_id: str, source_type: str, label: str
) -> SourceStatus:
    manifest = _last_successful_import(session, profile_id, source_type)
    if manifest is None:
        return SourceStatus(name=label, configured=True, status="never_imported")
    age_days = (datetime.now(UTC) - manifest.finished_at).days if manifest.finished_at else None
    stale = age_days is not None and age_days > 30
    return SourceStatus(
        name=label,
        configured=True,
        status="stale" if stale else "ok",
        detail=f"Last import {age_days}d ago, {manifest.records_processed} records"
        if age_days is not None
        else None,
    )


def get_data_status(session: Session, profile_id: str, settings: Settings) -> list[SourceStatus]:
    statuses = [
        _import_source_status(session, profile_id, "apple_health", "Apple Health"),
        _import_source_status(session, profile_id, "sports_tracker", "Sports Tracker"),
    ]

    statuses.append(
        SourceStatus(
            name="Outlook",
            configured=settings.calendar_configured,
            status="ok" if settings.calendar_configured else "not_configured",
        )
    )
    statuses.append(
        SourceStatus(
            name="Weather",
            configured=settings.weather_configured,
            status="ok" if settings.weather_configured else "not_configured",
        )
    )
    statuses.append(
        SourceStatus(
            name="LLM (OpenAI)",
            configured=settings.llm_configured,
            status="ok" if settings.llm_configured else "not_configured",
            detail=None if settings.llm_configured else "Deterministic-only planning will be used.",
        )
    )

    lab_results = clinical_repo.list_lab_results(session, profile_id)
    statuses.append(
        SourceStatus(
            name="Clinical/lab data",
            configured=True,
            status="ok" if lab_results else "never_imported",
            detail=f"{len(lab_results)} results on file" if lab_results else None,
        )
    )

    body_comp = clinical_repo.list_body_composition(session, profile_id)
    statuses.append(
        SourceStatus(
            name="Body composition",
            configured=True,
            status="ok" if body_comp else "never_imported",
            detail=f"{len(body_comp)} assessments on file" if body_comp else None,
        )
    )

    return statuses
