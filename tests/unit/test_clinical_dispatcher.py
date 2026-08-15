from __future__ import annotations

from sophie.providers.clinical import detect_and_import_clinical_file


def test_dispatch_csv(tmp_path):
    path = tmp_path / "labs.csv"
    path.write_text("date,test,value,unit\n2026-06-01,HbA1c,5.4,%\n", encoding="utf-8")
    outcome = detect_and_import_clinical_file(path)
    assert len(outcome.results) == 1


def test_dispatch_json(tmp_path):
    path = tmp_path / "labs.json"
    path.write_text(
        '{"results": [{"date": "2026-06-01", "test": "HbA1c", "value": 5.4, "unit": "%"}]}',
        encoding="utf-8",
    )
    outcome = detect_and_import_clinical_file(path)
    assert len(outcome.results) == 1


def test_dispatch_unsupported_extension(tmp_path):
    path = tmp_path / "labs.txt"
    path.write_text("not supported", encoding="utf-8")
    outcome = detect_and_import_clinical_file(path)
    assert outcome.results == []
    assert outcome.warnings
