"""Orchestrates a full Apple Health import: idempotence check, safe
extraction, streaming parse, and persistence via repositories. See
docs/PRODUCT_SPEC.md §9-15 and docs/PRIVACY.md — the ZIP/XML is never
persisted; only normalized rows are.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from sophie.providers.apple_health import (
    AppleHealthImportError,
    extract_apple_health_export,
    parse_apple_health_export,
)
from sophie.repositories import import_repo, summary_repo
from sophie.services.fingerprint import compute_file_fingerprint
from sophie.services.workout_canonicalization import persist_raw_workouts

SOURCE_TYPE = "apple_health"


@dataclass
class ImportSummary:
    state: str  # success/partial/failed/skipped_duplicate
    records_processed: int = 0
    workouts_created: int = 0
    workouts_matched: int = 0
    daily_samples_written: int = 0
    catalog_entries_written: int = 0
    warnings: list[str] | None = None
    error_summary: str | None = None


def import_apple_health_zip(
    session: Session, profile_id: str, zip_path: str | Path
) -> ImportSummary:
    fingerprint = compute_file_fingerprint(zip_path)

    existing = import_repo.find_manifest_by_fingerprint(session, profile_id, fingerprint)
    if existing is not None:
        return ImportSummary(
            state="skipped_duplicate", warnings=["Identical file already imported."]
        )

    manifest = import_repo.start_manifest(session, profile_id, SOURCE_TYPE, fingerprint)

    try:
        with tempfile.TemporaryDirectory(prefix="sophie_apple_health_") as tmp_dir:
            extract_dir = Path(tmp_dir) / "extracted"
            with extract_apple_health_export(zip_path, extract_dir) as export_xml:
                outcome = parse_apple_health_export(export_xml)
    except AppleHealthImportError as exc:
        import_repo.finish_manifest(
            session, manifest, state="failed", records_processed=0, error_summary=str(exc)
        )
        return ImportSummary(state="failed", error_summary=str(exc))

    canonicalization = persist_raw_workouts(session, profile_id, outcome.workouts, manifest.id)

    for sample in outcome.daily_samples:
        summary_repo.upsert_daily_summary(
            session, profile_id, sample.day, **{sample.field: sample.value}
        )

    for entry in outcome.catalog_entries:
        import_repo.upsert_metric_catalog_entry(
            session,
            profile_id,
            record_type=entry.record_type,
            friendly_name=entry.friendly_name,
            first_seen_at=entry.first_seen_at,
            last_seen_at=entry.last_seen_at,
            count_increment=entry.count,
            unit=entry.unit,
            status=entry.status,
            sophie_use=entry.sophie_use,
        )

    state = "partial" if outcome.warnings else "success"
    import_repo.finish_manifest(
        session,
        manifest,
        state=state,
        records_processed=outcome.records_processed,
        warnings=outcome.warnings,
    )

    return ImportSummary(
        state=state,
        records_processed=outcome.records_processed,
        workouts_created=canonicalization.created,
        workouts_matched=canonicalization.matched,
        daily_samples_written=len(outcome.daily_samples),
        catalog_entries_written=len(outcome.catalog_entries),
        warnings=outcome.warnings,
    )
