from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path

import pytest

from sophie.providers.apple_health import (
    AppleHealthImportError,
    extract_apple_health_export,
    parse_apple_health_export,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
<ExportDate value="2026-08-15 10:00:00 +0000"/>
<Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Health" unit="kg"
 startDate="2026-08-01 08:00:00 +0000" endDate="2026-08-01 08:00:00 +0000" value="90.2"/>
<Record type="HKQuantityTypeIdentifierStepCount" sourceName="Watch" unit="count"
 startDate="2026-08-01 09:00:00 +0000" endDate="2026-08-01 09:05:00 +0000" value="500"/>
<Record type="HKQuantityTypeIdentifierStepCount" sourceName="Watch" unit="count"
 startDate="2026-08-01 12:00:00 +0000" endDate="2026-08-01 12:05:00 +0000" value="700"/>
<Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Watch" unit="count/min"
 startDate="2026-08-01 06:00:00 +0000" endDate="2026-08-01 06:00:00 +0000" value="52"/>
<Record type="HKQuantityTypeIdentifierWalkingAsymmetryPercentage" sourceName="Watch" unit="%"
 startDate="2026-08-01 09:00:00 +0000" endDate="2026-08-01 09:05:00 +0000" value="3"/>
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch"
 startDate="2026-08-01 23:30:00 +0000" endDate="2026-08-02 07:00:00 +0000"
 value="HKCategoryValueSleepAnalysisAsleepCore"/>
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch"
 startDate="2026-08-01 22:00:00 +0000" endDate="2026-08-01 23:00:00 +0000"
 value="HKCategoryValueSleepAnalysisInBed"/>
<Workout workoutActivityType="HKWorkoutActivityTypeRunning" sourceName="Watch"
 duration="42" durationUnit="min" totalDistance="10" totalDistanceUnit="km"
 startDate="2026-08-01 08:00:00 +0000" endDate="2026-08-01 08:42:00 +0000">
  <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate"
   average="145" maximum="172" unit="count/min"/>
</Workout>
<Record type="NotAnAttribute" startDate="not-a-date" value="oops"/>
</HealthData>
"""

MALFORMED_XML = '<HealthData><Record type="HKQuantityTypeIdentifierBodyMass" value="90"'


def test_parse_apple_health_export_basic(tmp_path):
    xml_path = tmp_path / "export.xml"
    xml_path.write_text(SAMPLE_XML, encoding="utf-8")

    outcome = parse_apple_health_export(xml_path)

    assert outcome.records_processed >= 8
    weight_samples = [s for s in outcome.daily_samples if s.field == "weight_kg"]
    assert weight_samples and weight_samples[0].value == 90.2

    step_samples = [s for s in outcome.daily_samples if s.field == "steps"]
    assert step_samples and step_samples[0].value == 1200  # summed

    sleep_samples = [s for s in outcome.daily_samples if s.field == "sleep_minutes"]
    assert sleep_samples and sleep_samples[0].day == date(2026, 8, 2)
    assert sleep_samples[0].value == pytest.approx(450, rel=0.01)  # 7.5h of "asleep" only

    assert len(outcome.workouts) == 1
    workout = outcome.workouts[0]
    assert workout.activity_type == "run"
    assert workout.distance_m == 10000
    assert workout.avg_hr == 145
    assert workout.max_hr == 172

    catalog_types = {c.record_type: c for c in outcome.catalog_entries}
    assert (
        catalog_types["HKQuantityTypeIdentifierWalkingAsymmetryPercentage"].status
        == "deliberately_excluded"
    )
    assert catalog_types["HKQuantityTypeIdentifierBodyMass"].status == "actively_used"
    assert "NotAnAttribute" in catalog_types
    assert catalog_types["NotAnAttribute"].status == "recognized_unused"


def test_overlapping_sleep_records_are_merged_not_summed(tmp_path):
    """Regression test: real Apple Health exports commonly contain
    overlapping sleep records for the same night from multiple sources (e.g.
    a coarse "Asleep" summary alongside per-stage Core/Deep/REM breakdowns
    covering the same wall-clock time). Naively summing every record's
    duration double-counts the overlap; merging to a union of intervals
    gives the true ~8h, not ~13h+."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
<ExportDate value="2026-08-15 10:00:00 +0000"/>
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="iPhone"
 startDate="2026-08-01 23:00:00 +0000" endDate="2026-08-02 07:00:00 +0000"
 value="HKCategoryValueSleepAnalysisAsleep"/>
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch"
 startDate="2026-08-01 23:00:00 +0000" endDate="2026-08-02 01:30:00 +0000"
 value="HKCategoryValueSleepAnalysisAsleepCore"/>
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch"
 startDate="2026-08-02 01:30:00 +0000" endDate="2026-08-02 03:00:00 +0000"
 value="HKCategoryValueSleepAnalysisAsleepDeep"/>
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch"
 startDate="2026-08-02 03:00:00 +0000" endDate="2026-08-02 07:00:00 +0000"
 value="HKCategoryValueSleepAnalysisAsleepREM"/>
</HealthData>
"""
    xml_path = tmp_path / "export.xml"
    xml_path.write_text(xml, encoding="utf-8")

    outcome = parse_apple_health_export(xml_path)

    sleep_samples = [s for s in outcome.daily_samples if s.field == "sleep_minutes"]
    assert len(sleep_samples) == 1
    # True union is 23:00 -> 07:00 = 8h = 480min, NOT the naive sum of all four
    # overlapping/adjacent records (8h + 2.5h + 1.5h + 4h = 16h).
    assert sleep_samples[0].value == pytest.approx(480, rel=0.01)


def test_parse_malformed_xml_with_zero_records_raises(tmp_path):
    xml_path = tmp_path / "export.xml"
    xml_path.write_text(MALFORMED_XML, encoding="utf-8")

    with pytest.raises(AppleHealthImportError):
        parse_apple_health_export(xml_path)


def test_xxe_entity_is_not_resolved(tmp_path):
    evil_file = tmp_path / "secret.txt"
    evil_file.write_text("SECRET_CONTENT", encoding="utf-8")
    xxe_xml = f"""<?xml version="1.0"?>
<!DOCTYPE HealthData [<!ENTITY xxe SYSTEM "file://{evil_file}">]>
<HealthData>
<Record type="HKQuantityTypeIdentifierBodyMass" sourceName="&xxe;" unit="kg"
 startDate="2026-08-01 08:00:00 +0000" endDate="2026-08-01 08:00:00 +0000" value="90"/>
</HealthData>
"""
    xml_path = tmp_path / "export.xml"
    xml_path.write_text(xxe_xml, encoding="utf-8")

    # Either the entity is safely left unresolved (parse succeeds without leaking
    # secret content) or the parser rejects the DTD/entity outright — either way,
    # SECRET_CONTENT must never appear in the parsed output.
    try:
        outcome = parse_apple_health_export(xml_path)
    except AppleHealthImportError:
        return
    for sample in outcome.daily_samples:
        assert "SECRET_CONTENT" not in repr(sample)


def _make_zip(tmp_path, entries: dict[str, bytes]) -> Path:
    zip_path = Path(tmp_path) / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return zip_path


def test_extract_apple_health_export_happy_path(tmp_path):
    zip_path = _make_zip(tmp_path, {"apple_health_export/export.xml": SAMPLE_XML.encode("utf-8")})
    extract_dir = tmp_path / "extracted"
    with extract_apple_health_export(zip_path, extract_dir) as export_xml:
        assert export_xml.exists()
        assert export_xml.read_text(encoding="utf-8").startswith("<?xml")
    assert not extract_dir.exists()  # cleaned up


def test_extract_missing_export_xml_raises(tmp_path):
    zip_path = _make_zip(tmp_path, {"apple_health_export/readme.txt": b"nothing here"})
    extract_dir = tmp_path / "extracted2"
    with pytest.raises(AppleHealthImportError):
        with extract_apple_health_export(zip_path, extract_dir):
            pass


def test_extract_rejects_zip_slip(tmp_path):
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("apple_health_export/export.xml", SAMPLE_XML)
        zf.writestr("../../evil.txt", b"pwned")
    extract_dir = tmp_path / "extracted3"
    with extract_apple_health_export(zip_path, extract_dir) as export_xml:
        assert export_xml.exists()
    escaped_path = tmp_path.parent.parent / "evil.txt"
    assert not escaped_path.exists()


def test_extract_malformed_zip_raises(tmp_path):
    zip_path = Path(tmp_path) / "corrupt.zip"
    zip_path.write_bytes(b"not a real zip file at all")
    extract_dir = tmp_path / "extracted4"
    with pytest.raises(AppleHealthImportError):
        with extract_apple_health_export(zip_path, extract_dir):
            pass
