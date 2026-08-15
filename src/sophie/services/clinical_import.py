"""Orchestrates clinical lab + body composition import. CSV/JSON are
structured data the user pointed Sophie at directly, so they persist
immediately. PDF extraction is inherently uncertain (see
docs/HEALTH_LOGIC_AND_SAFETY.md and docs/PRODUCT_SPEC.md §30) — its results
are returned for UI review and only persisted via
`confirm_and_persist_lab_results()` once the user has explicitly confirmed
them (editing values first if needed). Nothing here trusts a PDF-derived
value automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from sophie.db.models import ClinicalImport
from sophie.domain.import_types import ClinicalImportOutcome, ParsedBodyComposition, ParsedLabResult
from sophie.providers.clinical import (
    import_body_composition_csv,
    import_body_composition_json,
    import_lab_results_csv,
    import_lab_results_json,
    import_lab_results_pdf,
)
from sophie.repositories import clinical_repo

_SOURCE_KIND_BY_SUFFIX = {".csv": "csv", ".json": "json", ".pdf": "pdf_confirmed"}


@dataclass
class ClinicalImportResponse:
    outcome: ClinicalImportOutcome
    persisted: bool
    clinical_import_id: str | None = None


def import_lab_result_file(
    session: Session, profile_id: str, path: str | Path, provider_name: str | None
) -> ClinicalImportResponse:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        outcome = import_lab_results_csv(file_path)
    elif suffix == ".json":
        outcome = import_lab_results_json(file_path)
    elif suffix == ".pdf":
        outcome = import_lab_results_pdf(file_path)
    else:
        outcome = ClinicalImportOutcome(warnings=[f"Unsupported file type: {suffix or '(none)'}"])

    if outcome.requires_confirmation or not outcome.results:
        return ClinicalImportResponse(outcome=outcome, persisted=False)

    source_kind = _SOURCE_KIND_BY_SUFFIX.get(suffix, "csv")
    clinical_import = _persist(
        session, profile_id, provider_name, source_kind, outcome.results, confirmed=True
    )
    return ClinicalImportResponse(
        outcome=outcome, persisted=True, clinical_import_id=clinical_import.id
    )


def confirm_and_persist_lab_results(
    session: Session,
    profile_id: str,
    provider_name: str | None,
    results: list[ParsedLabResult],
) -> str:
    """Called after the user has reviewed (and possibly edited) PDF-derived
    results in the UI and explicitly confirmed them."""

    clinical_import = _persist(
        session, profile_id, provider_name, "pdf_confirmed", results, confirmed=True
    )
    return clinical_import.id


def _persist(
    session: Session,
    profile_id: str,
    provider_name: str | None,
    source_kind: str,
    results: list[ParsedLabResult],
    confirmed: bool,
) -> ClinicalImport:
    clinical_import = clinical_repo.create_clinical_import(
        session,
        profile_id=profile_id,
        provider=provider_name,
        source_kind=source_kind,
        imported_at=datetime.now(UTC),
        user_confirmed=confirmed,
    )
    for result in results:
        clinical_repo.add_lab_result(
            session,
            profile_id=profile_id,
            clinical_import_id=clinical_import.id,
            sample_date=result.sample_date,
            test_name=result.test_name,
            canonical_test_id=result.canonical_test_id,
            value=result.value,
            value_text=result.value_text,
            unit=result.unit,
            reference_low=result.reference_low,
            reference_high=result.reference_high,
            reference_text=result.reference_text,
            abnormal_flag=result.abnormal_flag,
            category=result.category,
            notes=result.notes,
        )
    return clinical_import


def import_body_composition_file(
    session: Session, profile_id: str, path: str | Path
) -> list[ParsedBodyComposition]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        assessments = import_body_composition_csv(file_path)
    elif suffix == ".json":
        assessments = import_body_composition_json(file_path)
    else:
        return []

    for assessment in assessments:
        clinical_repo.add_body_composition(
            session,
            profile_id=profile_id,
            assessed_at=assessment.assessed_at,
            method=assessment.method,
            provider=assessment.provider,
            weight_kg=assessment.weight_kg,
            body_fat_pct=assessment.body_fat_pct,
            lean_mass_kg=assessment.lean_mass_kg,
            segmental_json=assessment.segmental,
            visceral_metric=assessment.visceral_metric,
            notes=assessment.notes,
        )
    return assessments
