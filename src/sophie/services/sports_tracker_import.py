"""Orchestrates a Sports Tracker import: idempotence check, safe extraction,
FIT/GPX parsing, and persistence via the shared canonicalization service. See
docs/PRODUCT_SPEC.md §12-15 and docs/PRIVACY.md — the ZIP/FIT/GPX files are
never persisted; only normalized rows are.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from sophie.providers.sports_tracker import import_sports_tracker_zip
from sophie.repositories import import_repo
from sophie.services.fingerprint import compute_file_fingerprint
from sophie.services.workout_canonicalization import persist_raw_workouts

SOURCE_TYPE = "sports_tracker"


@dataclass
class ImportSummary:
    state: str  # success/partial/failed/skipped_duplicate
    records_processed: int = 0
    workouts_created: int = 0
    workouts_matched: int = 0
    warnings: list[str] | None = None
    error_summary: str | None = None


def import_sports_tracker_zip_file(
    session: Session, profile_id: str, zip_path: str | Path
) -> ImportSummary:
    fingerprint = compute_file_fingerprint(zip_path)

    existing = import_repo.find_manifest_by_fingerprint(session, profile_id, fingerprint)
    if existing is not None:
        return ImportSummary(
            state="skipped_duplicate", warnings=["Identical file already imported."]
        )

    manifest = import_repo.start_manifest(session, profile_id, SOURCE_TYPE, fingerprint)

    with tempfile.TemporaryDirectory(prefix="sophie_sports_tracker_") as tmp_dir:
        extract_dir = Path(tmp_dir) / "extracted"
        outcome = import_sports_tracker_zip(zip_path, extract_dir)

    canonicalization = persist_raw_workouts(session, profile_id, outcome.workouts, manifest.id)

    state = "partial" if outcome.warnings else "success"
    if not outcome.workouts and outcome.warnings:
        state = "failed"

    import_repo.finish_manifest(
        session,
        manifest,
        state=state,
        records_processed=outcome.records_processed,
        warnings=outcome.warnings,
        error_summary=(outcome.warnings[0] if state == "failed" else None),
    )

    return ImportSummary(
        state=state,
        records_processed=outcome.records_processed,
        workouts_created=canonicalization.created,
        workouts_matched=canonicalization.matched,
        warnings=outcome.warnings,
    )
