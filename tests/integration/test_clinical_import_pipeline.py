from __future__ import annotations

from datetime import date

from sophie.domain.import_types import ParsedLabResult
from sophie.repositories import clinical_repo, profile_repo
from sophie.services.clinical_import import confirm_and_persist_lab_results, import_lab_result_file


def test_csv_lab_import_persists_immediately(db_session, tmp_path):
    profile = profile_repo.get_or_create_profile(db_session)
    csv_path = tmp_path / "labs.csv"
    csv_path.write_text(
        "date,test,value,unit,reference_range\n2026-06-01,HbA1c,5.4,%,4.0-6.0\n", encoding="utf-8"
    )

    response = import_lab_result_file(db_session, profile.id, csv_path, provider_name="Avonova")

    assert response.persisted is True
    results = clinical_repo.list_lab_results(db_session, profile.id)
    assert len(results) == 1
    assert results[0].canonical_test_id == "hba1c"


def test_pdf_import_requires_confirmation_before_persisting(db_session, tmp_path, monkeypatch):
    profile = profile_repo.get_or_create_profile(db_session)

    from sophie.domain.import_types import ClinicalImportOutcome

    fake_outcome = ClinicalImportOutcome(
        results=[
            ParsedLabResult(
                sample_date=date(2026, 6, 1),
                test_name="HbA1c",
                canonical_test_id="hba1c",
                value=5.4,
                value_text=None,
                unit="%",
                reference_low=4.0,
                reference_high=6.0,
                reference_text="4.0-6.0",
                abnormal_flag=None,
                category="glucose",
            )
        ],
        requires_confirmation=True,
    )

    import sophie.services.clinical_import as clinical_import_module

    monkeypatch.setattr(clinical_import_module, "import_lab_results_pdf", lambda path: fake_outcome)

    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    response = import_lab_result_file(db_session, profile.id, pdf_path, provider_name="Avonova")
    assert response.persisted is False
    assert clinical_repo.list_lab_results(db_session, profile.id) == []

    confirm_and_persist_lab_results(db_session, profile.id, "Avonova", fake_outcome.results)
    results = clinical_repo.list_lab_results(db_session, profile.id)
    assert len(results) == 1
