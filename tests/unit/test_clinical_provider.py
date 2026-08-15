"""Tests for the provider-independent clinical import package
(sophie.providers.clinical). All fixtures here are synthetic — never real
lab data, per docs/PRIVACY.md."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sophie.domain.clinical_safety import contains_forbidden_language
from sophie.providers.clinical.body_composition_import import (
    import_body_composition_csv,
    import_body_composition_json,
)
from sophie.providers.clinical.csv_import import import_lab_results_csv
from sophie.providers.clinical.json_import import import_lab_results_json
from sophie.providers.clinical.pdf_import import SCANNED_IMAGE_WARNING, import_lab_results_pdf

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def test_csv_clean_import_mixed_reference_ranges(tmp_path: Path) -> None:
    csv_text = (
        "date,test,value,unit,reference_range\n"
        "2026-01-10,Hemoglobin,145,g/L,117-155\n"
        "2026-01-10,TSH,2.1,mIU/L,0.4-4.0\n"
        "2026-01-10,ANA,Positive,,Negative\n"
    )
    path = tmp_path / "labs.csv"
    path.write_text(csv_text, encoding="utf-8")

    outcome = import_lab_results_csv(path)

    assert outcome.requires_confirmation is False
    assert outcome.warnings == []
    assert len(outcome.results) == 3

    hgb = outcome.results[0]
    assert hgb.test_name == "Hemoglobin"
    assert hgb.canonical_test_id == "hemoglobin"
    assert hgb.category == "blood_count"
    assert hgb.value == 145.0
    assert hgb.unit == "g/L"
    assert hgb.reference_low == 117.0
    assert hgb.reference_high == 155.0
    assert hgb.reference_text == "117-155"
    assert hgb.abnormal_flag is None

    ana = outcome.results[2]
    assert ana.canonical_test_id == "ana"
    assert ana.category == "autoimmune"
    # Non-numeric result text is preserved verbatim, never guessed at.
    assert ana.value is None
    assert ana.value_text == "Positive"
    # Non-numeric reference text that isn't a "low-high" range is kept
    # verbatim and not force-parsed into bounds.
    assert ana.reference_text == "Negative"
    assert ana.reference_low is None
    assert ana.reference_high is None


def test_csv_preserves_lab_supplied_abnormal_flag(tmp_path: Path) -> None:
    csv_text = (
        "sample_date,test_name,result,unit,ref_low,ref_high,abnormal_flag\n"
        "2026-02-01,Ferritin,8,ug/L,20,250,L\n"
    )
    path = tmp_path / "labs.csv"
    path.write_text(csv_text, encoding="utf-8")

    outcome = import_lab_results_csv(path)

    assert len(outcome.results) == 1
    result = outcome.results[0]
    assert result.canonical_test_id == "ferritin"
    assert result.value == 8.0
    assert result.reference_low == 20.0
    assert result.reference_high == 250.0
    # The flag came straight from the source file, never computed by the
    # provider even though the value (8) is below the reference_low (20).
    assert result.abnormal_flag == "L"


def test_csv_malformed_row_skipped_with_warning_not_crash(tmp_path: Path) -> None:
    csv_text = (
        "date,test,value,unit,reference_range\n"
        "2026-01-10,Hemoglobin,145,g/L,117-155\n"
        "not-a-date,Glucose,5.4,mmol/L,4.0-6.0\n"
        ",,,,\n"
    )
    path = tmp_path / "labs.csv"
    path.write_text(csv_text, encoding="utf-8")

    outcome = import_lab_results_csv(path)

    # The clean row still imports; the malformed one is skipped with a
    # warning rather than raising.
    assert len(outcome.results) == 1
    assert outcome.results[0].test_name == "Hemoglobin"
    assert len(outcome.warnings) == 1
    assert "Row 3" in outcome.warnings[0]


def test_csv_missing_header_row_returns_no_results(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    outcome = import_lab_results_csv(path)

    assert outcome.results == []
    assert outcome.warnings != []


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def test_json_list_form_import(tmp_path: Path) -> None:
    payload: list[dict[str, Any]] = [
        {
            "sampleDate": "2026-03-05",
            "testName": "LDL Cholesterol",
            "value": 3.2,
            "unit": "mmol/L",
            "referenceHigh": 3.0,
            "referenceLow": 0,
        },
    ]
    path = tmp_path / "labs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    outcome = import_lab_results_json(path)

    assert outcome.requires_confirmation is False
    assert len(outcome.results) == 1
    result = outcome.results[0]
    assert result.canonical_test_id == "ldl_cholesterol"
    assert result.value == 3.2
    assert result.reference_low == 0.0
    assert result.reference_high == 3.0


def test_json_results_wrapper_form_import(tmp_path: Path) -> None:
    payload = {
        "results": [
            {
                "date": "2026-03-05",
                "test": "Vitamin D",
                "result": 45,
                "unit": "nmol/L",
                "reference_range": "50-125",
            },
        ],
    }
    path = tmp_path / "labs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    outcome = import_lab_results_json(path)

    assert len(outcome.results) == 1
    result = outcome.results[0]
    assert result.canonical_test_id == "vitamin_d"
    assert result.value == 45.0
    assert result.reference_low == 50.0
    assert result.reference_high == 125.0


def test_json_missing_required_field_skipped_with_warning(tmp_path: Path) -> None:
    payload = {
        "labs": [
            {"date": "2026-03-05", "test": "Vitamin D", "result": 45},
            {"test": "Vitamin B12", "result": 300},  # missing date
        ],
    }
    path = tmp_path / "labs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    outcome = import_lab_results_json(path)

    assert len(outcome.results) == 1
    assert len(outcome.warnings) == 1
    assert "Item 1" in outcome.warnings[0]


def test_json_unrecognized_shape_returns_warning(tmp_path: Path) -> None:
    path = tmp_path / "labs.json"
    path.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")

    outcome = import_lab_results_json(path)

    assert outcome.results == []
    assert outcome.warnings != []


# ---------------------------------------------------------------------------
# PDF (pdfplumber monkeypatched — no real PDF writer available)
# ---------------------------------------------------------------------------


class _FakePage:
    def __init__(
        self,
        tables: list[list[list[str | None]]] | None = None,
        text: str | None = None,
    ) -> None:
        self._tables = tables or []
        self._text = text

    def extract_tables(self) -> list[list[list[str | None]]]:
        return self._tables

    def extract_text(self) -> str | None:
        return self._text


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self) -> _FakePdf:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_pdf_clean_extractable_table_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    table = [
        ["Test", "Result", "Unit", "Reference range"],
        ["Hemoglobin", "145", "g/L", "117-155"],
        ["Glucose", "5.4", "mmol/L", "4.0-6.0"],
    ]
    page = _FakePage(
        tables=[table],
        text="Report date: 2026-04-01\nHemoglobin 145 g/L (117-155)\nGlucose 5.4 mmol/L (4.0-6.0)",
    )
    fake_pdf = _FakePdf([page])

    monkeypatch.setattr(
        "sophie.providers.clinical.pdf_import.pdfplumber.open",
        lambda _path: fake_pdf,
    )

    outcome = import_lab_results_pdf(Path("fake.pdf"))

    assert outcome.requires_confirmation is True
    assert len(outcome.results) == 2
    names = {r.test_name for r in outcome.results}
    assert names == {"Hemoglobin", "Glucose"}
    hgb = next(r for r in outcome.results if r.test_name == "Hemoglobin")
    assert hgb.value == 145.0
    assert hgb.reference_low == 117.0
    assert hgb.reference_high == 155.0
    assert hgb.sample_date.isoformat() == "2026-04-01"


def test_pdf_scanned_image_no_text_returns_zero_results_and_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _FakePage(tables=[], text=None)
    fake_pdf = _FakePdf([page])

    monkeypatch.setattr(
        "sophie.providers.clinical.pdf_import.pdfplumber.open",
        lambda _path: fake_pdf,
    )

    outcome = import_lab_results_pdf(Path("scanned.pdf"))

    assert outcome.results == []
    assert outcome.requires_confirmation is True
    assert SCANNED_IMAGE_WARNING in outcome.warnings


def test_pdf_ambiguous_text_line_skipped_with_warning_not_guessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = (
        "Report date: 2026-05-01\n"
        "Hemoglobin      145  g/L   (117 - 155)\n"
        "Patient reported feeling well; see comments p.2\n"
    )
    page = _FakePage(tables=[], text=text)
    fake_pdf = _FakePdf([page])

    monkeypatch.setattr(
        "sophie.providers.clinical.pdf_import.pdfplumber.open",
        lambda _path: fake_pdf,
    )

    outcome = import_lab_results_pdf(Path("report.pdf"))

    assert outcome.requires_confirmation is True
    assert len(outcome.results) == 1
    assert outcome.results[0].test_name == "Hemoglobin"
    # The ambiguous free-text line is skipped, not guessed at, and produces
    # a warning describing what could not be parsed.
    assert any("could not confidently parse" in w for w in outcome.warnings)


# ---------------------------------------------------------------------------
# Body composition
# ---------------------------------------------------------------------------


def test_body_composition_csv_json_round_trip(tmp_path: Path) -> None:
    csv_text = (
        "assessed_at,method,provider,weight_kg,body_fat_pct,lean_mass_kg,visceral_metric\n"
        "2026-01-15,DEXA,Clinic A,82.5,18.2,64.1,7\n"
    )
    csv_path = tmp_path / "bodycomp.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    csv_results = import_body_composition_csv(csv_path)
    assert len(csv_results) == 1
    csv_entry = csv_results[0]
    assert csv_entry.method == "DEXA"
    assert csv_entry.provider == "Clinic A"
    assert csv_entry.weight_kg == 82.5
    assert csv_entry.body_fat_pct == 18.2
    assert csv_entry.lean_mass_kg == 64.1
    assert csv_entry.visceral_metric == 7.0

    json_payload = {
        "results": [
            {
                "assessed_at": "2026-01-15",
                "measurement_method": "bioimpedance",
                "provider": "Home scale",
                "weight": 82.1,
                "bodyfat": 19.0,
                "lean_mass": 63.0,
                "visceral": 6,
                "segmental": {"left_arm_pct": 17.5, "right_arm_pct": 17.8},
            },
        ],
    }
    json_path = tmp_path / "bodycomp.json"
    json_path.write_text(json.dumps(json_payload), encoding="utf-8")

    json_results = import_body_composition_json(json_path)
    assert len(json_results) == 1
    json_entry = json_results[0]
    assert json_entry.method == "bioimpedance"
    assert json_entry.provider == "Home scale"
    assert json_entry.weight_kg == 82.1
    assert json_entry.body_fat_pct == 19.0
    assert json_entry.lean_mass_kg == 63.0
    assert json_entry.visceral_metric == 6.0
    # Segmental data is passed through as-is, not normalized/interpreted.
    assert json_entry.segmental == {"left_arm_pct": 17.5, "right_arm_pct": 17.8}

    # DEXA and bioimpedance results are never merged/compared by this
    # provider — that's a service/UI concern. Each retains its own method.
    assert {csv_entry.method, json_entry.method} == {"DEXA", "bioimpedance"}


def test_body_composition_missing_date_row_skipped(tmp_path: Path) -> None:
    csv_text = "assessed_at,method,weight_kg\n2026-01-15,DEXA,82.5\n,bioimpedance,81.0\n"
    path = tmp_path / "bodycomp.csv"
    path.write_text(csv_text, encoding="utf-8")

    results = import_body_composition_csv(path)

    assert len(results) == 1
    assert results[0].method == "DEXA"


# ---------------------------------------------------------------------------
# Safety: this provider's own warning strings never state/imply a diagnosis
# ---------------------------------------------------------------------------


def test_provider_warnings_never_contain_forbidden_language(tmp_path: Path) -> None:
    malformed_csv = "date,test,value,unit,reference_range\nnot-a-date,Glucose,5.4,mmol/L,4.0-6.0\n"
    csv_path = tmp_path / "labs.csv"
    csv_path.write_text(malformed_csv, encoding="utf-8")
    csv_outcome = import_lab_results_csv(csv_path)

    bad_json_path = tmp_path / "labs.json"
    bad_json_path.write_text(json.dumps({"nope": "shape"}), encoding="utf-8")
    json_outcome = import_lab_results_json(bad_json_path)

    all_warnings = [
        *csv_outcome.warnings,
        *json_outcome.warnings,
        SCANNED_IMAGE_WARNING,
    ]

    for warning in all_warnings:
        assert contains_forbidden_language(warning) is False, warning
