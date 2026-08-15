from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import AppleHealthMetricCatalog, ImportManifest

IMPORTER_VERSION = "1"


def find_manifest_by_fingerprint(
    session: Session, profile_id: str, fingerprint: str
) -> ImportManifest | None:
    return session.execute(
        select(ImportManifest).where(
            ImportManifest.profile_id == profile_id,
            ImportManifest.content_fingerprint == fingerprint,
            ImportManifest.state == "success",
        )
    ).scalar_one_or_none()


def start_manifest(
    session: Session, profile_id: str, source_type: str, fingerprint: str
) -> ImportManifest:
    manifest = ImportManifest(
        profile_id=profile_id,
        source_type=source_type,
        content_fingerprint=fingerprint,
        importer_version=IMPORTER_VERSION,
        started_at=datetime.now(UTC),
        state="pending",
    )
    session.add(manifest)
    session.flush()
    return manifest


def finish_manifest(
    session: Session,
    manifest: ImportManifest,
    state: str,
    records_processed: int,
    duplicates_detected: int = 0,
    warnings: list[str] | None = None,
    error_summary: str | None = None,
) -> ImportManifest:
    manifest.state = state
    manifest.finished_at = datetime.now(UTC)
    manifest.records_processed = records_processed
    manifest.duplicates_detected = duplicates_detected
    manifest.warnings = warnings or []
    manifest.error_summary = error_summary
    session.flush()
    return manifest


def upsert_metric_catalog_entry(
    session: Session,
    profile_id: str,
    record_type: str,
    friendly_name: str,
    first_seen_at: datetime | None,
    last_seen_at: datetime | None,
    count_increment: int,
    unit: str | None,
    status: str,
    sophie_use: str | None,
) -> AppleHealthMetricCatalog:
    entry = session.execute(
        select(AppleHealthMetricCatalog).where(
            AppleHealthMetricCatalog.profile_id == profile_id,
            AppleHealthMetricCatalog.record_type == record_type,
        )
    ).scalar_one_or_none()
    if entry is None:
        entry = AppleHealthMetricCatalog(
            profile_id=profile_id,
            record_type=record_type,
            friendly_name=friendly_name,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
            approx_record_count=count_increment,
            unit=unit,
            status=status,
            sophie_use=sophie_use,
        )
        session.add(entry)
    else:
        entry.approx_record_count += count_increment
        if first_seen_at and (entry.first_seen_at is None or first_seen_at < entry.first_seen_at):
            entry.first_seen_at = first_seen_at
        if last_seen_at and (entry.last_seen_at is None or last_seen_at > entry.last_seen_at):
            entry.last_seen_at = last_seen_at
    session.flush()
    return entry


def list_metric_catalog(session: Session, profile_id: str) -> list[AppleHealthMetricCatalog]:
    return list(
        session.execute(
            select(AppleHealthMetricCatalog)
            .where(AppleHealthMetricCatalog.profile_id == profile_id)
            .order_by(AppleHealthMetricCatalog.record_type)
        ).scalars()
    )
