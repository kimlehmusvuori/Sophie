from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import (
    BodyCompositionAssessment,
    ClinicalImport,
    ClinicalSymptomNote,
    LabResult,
)


def create_clinical_import(session: Session, **fields: object) -> ClinicalImport:
    row = ClinicalImport(**fields)
    session.add(row)
    session.flush()
    return row


def add_lab_result(session: Session, **fields: object) -> LabResult:
    row = LabResult(**fields)
    session.add(row)
    session.flush()
    return row


def list_lab_results(
    session: Session, profile_id: str, canonical_test_id: str | None = None
) -> list[LabResult]:
    stmt = select(LabResult).where(LabResult.profile_id == profile_id)
    if canonical_test_id:
        stmt = stmt.where(LabResult.canonical_test_id == canonical_test_id)
    stmt = stmt.order_by(LabResult.sample_date)
    return list(session.execute(stmt).scalars())


def list_lab_categories(session: Session, profile_id: str) -> list[str]:
    rows = session.execute(
        select(LabResult.category).where(LabResult.profile_id == profile_id).distinct()
    ).scalars()
    return sorted(set(rows))


def add_body_composition(session: Session, **fields: object) -> BodyCompositionAssessment:
    row = BodyCompositionAssessment(**fields)
    session.add(row)
    session.flush()
    return row


def list_body_composition(session: Session, profile_id: str) -> list[BodyCompositionAssessment]:
    return list(
        session.execute(
            select(BodyCompositionAssessment)
            .where(BodyCompositionAssessment.profile_id == profile_id)
            .order_by(BodyCompositionAssessment.assessed_at)
        ).scalars()
    )


def add_symptom_note(
    session: Session, profile_id: str, entered_at: date, symptom: str, note: str | None
) -> ClinicalSymptomNote:
    row = ClinicalSymptomNote(
        profile_id=profile_id, entered_at=entered_at, symptom=symptom, note=note
    )
    session.add(row)
    session.flush()
    return row


def list_symptom_notes(session: Session, profile_id: str) -> list[ClinicalSymptomNote]:
    return list(
        session.execute(
            select(ClinicalSymptomNote)
            .where(ClinicalSymptomNote.profile_id == profile_id)
            .order_by(ClinicalSymptomNote.entered_at)
        ).scalars()
    )
