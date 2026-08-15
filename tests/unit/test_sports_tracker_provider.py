from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sophie.providers.sports_tracker.fit_parser import (
    extract_fit_workout,
    make_fit_source_identifier,
    parse_fit_file,
)
from sophie.providers.sports_tracker.gpx_parser import parse_gpx_bytes, parse_gpx_file
from sophie.providers.sports_tracker.zip_import import (
    dedupe_fit_gpx_pairs,
    import_sports_tracker_folder,
    import_sports_tracker_zip,
    safe_extract_zip,
)

# --------------------------------------------------------------------------
# Helpers to build fake fitparse-like objects (dependency injection, no real
# binary FIT file needed).
# --------------------------------------------------------------------------


def _make_fake_session(values: dict) -> MagicMock:
    session = MagicMock()
    session.get_value.side_effect = lambda name: values.get(name)
    return session


def _make_fake_record(values: dict) -> MagicMock:
    record = MagicMock()
    record.get_value.side_effect = lambda name: values.get(name)
    return record


def _make_fake_fit_file(sessions: list, records: list) -> MagicMock:
    fit_file = MagicMock()

    def get_messages(name=None):
        if name == "session":
            return iter(sessions)
        if name == "record":
            return iter(records)
        return iter([])

    fit_file.get_messages.side_effect = get_messages
    return fit_file


GPX_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">
  <trk>
    <name>{activity}</name>
    <trkseg>
      <trkpt lat="60.1699" lon="24.9384">
        <ele>10.0</ele>
        <time>{t0}</time>
        <extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>120</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions>
      </trkpt>
      <trkpt lat="60.1720" lon="24.9420">
        <ele>14.0</ele>
        <time>{t1}</time>
        <extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>150</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""


# --------------------------------------------------------------------------
# FIT: message-interpretation logic via injected fakes (no real binary FIT file)
# --------------------------------------------------------------------------


def test_extract_fit_workout_from_session_message():
    session = _make_fake_session(
        {
            "start_time": datetime(2026, 8, 1, 6, 0, 0),  # naive - as fitparse returns, UTC
            "total_timer_time": 1800.0,
            "total_elapsed_time": 1850.0,
            "total_distance": 5000.0,
            "sport": "running",
            "sub_sport": "generic",
            "avg_heart_rate": 145,
            "max_heart_rate": 170,
            "total_ascent": 50.0,
        }
    )
    fit_file = _make_fake_fit_file(sessions=[session], records=[])

    workout = extract_fit_workout(fit_file, "activity.fit")

    assert workout is not None
    assert workout.source_type == "sports_tracker_fit"
    assert workout.activity_type == "run"
    assert workout.start_at == datetime(2026, 8, 1, 6, 0, 0, tzinfo=UTC)
    assert workout.end_at == datetime(2026, 8, 1, 6, 30, 0, tzinfo=UTC)
    assert workout.duration_s == 1800
    assert workout.distance_m == 5000.0
    assert workout.avg_hr == 145.0
    assert workout.max_hr == 170.0
    assert workout.elevation_gain_m == 50.0
    assert workout.raw_activity_name == "running"
    # source_identifier is deterministic given the same inputs
    assert workout.source_identifier == make_fit_source_identifier(
        workout.start_at, "running", "activity.fit"
    )


def test_extract_fit_workout_unknown_sport_maps_to_other():
    session = _make_fake_session(
        {
            "start_time": datetime(2026, 8, 1, 6, 0, 0),
            "total_timer_time": 600.0,
            "sport": "some_unmapped_sport",
        }
    )
    fit_file = _make_fake_fit_file(sessions=[session], records=[])

    workout = extract_fit_workout(fit_file, "weird.fit")

    assert workout is not None
    assert workout.activity_type == "other"


def test_extract_fit_workout_falls_back_to_records_when_no_session():
    records = [
        _make_fake_record(
            {
                "timestamp": datetime(2026, 8, 1, 6, 0, 0),
                "heart_rate": 100,
                "altitude": 10.0,
                "distance": 0.0,
            }
        ),
        _make_fake_record(
            {
                "timestamp": datetime(2026, 8, 1, 6, 10, 0),
                "heart_rate": 160,
                "altitude": 40.0,
                "distance": 2000.0,
            }
        ),
    ]
    fit_file = _make_fake_fit_file(sessions=[], records=records)

    workout = extract_fit_workout(fit_file, "no_session.fit")

    assert workout is not None
    assert workout.start_at == datetime(2026, 8, 1, 6, 0, 0, tzinfo=UTC)
    assert workout.end_at == datetime(2026, 8, 1, 6, 10, 0, tzinfo=UTC)
    assert workout.duration_s == 600
    assert workout.distance_m == 2000.0
    assert workout.avg_hr == 130.0
    assert workout.max_hr == 160.0
    assert workout.elevation_gain_m == 30.0


def test_extract_fit_workout_returns_none_when_no_data_at_all():
    fit_file = _make_fake_fit_file(sessions=[], records=[])
    assert extract_fit_workout(fit_file, "empty.fit") is None


def test_parse_fit_file_handles_corrupt_binary_gracefully(tmp_path: Path):
    """Real entry point against deliberately corrupt/non-FIT bytes: must never raise,
    must return None and record a warning."""
    bad_fit = tmp_path / "corrupt.fit"
    bad_fit.write_bytes(b"this is not a fit file at all, just garbage bytes 0123456789")

    warnings: list[str] = []
    workout = parse_fit_file(bad_fit, warnings)

    assert workout is None
    assert warnings, "expected at least one warning for a corrupt FIT file"
    assert "corrupt.fit" in warnings[0]


def test_parse_fit_file_handles_missing_file_gracefully(tmp_path: Path):
    missing = tmp_path / "does_not_exist.fit"
    warnings: list[str] = []
    workout = parse_fit_file(missing, warnings)
    assert workout is None
    assert warnings


# --------------------------------------------------------------------------
# GPX: valid and malformed synthetic XML
# --------------------------------------------------------------------------


def test_parse_gpx_bytes_valid_track():
    xml = GPX_TEMPLATE.format(
        activity="Running", t0="2026-08-01T06:00:00Z", t1="2026-08-01T06:05:00Z"
    ).encode()

    workout, warnings = parse_gpx_bytes(xml, "run.gpx")

    assert warnings == []
    assert workout is not None
    assert workout.source_type == "sports_tracker_gpx"
    assert workout.activity_type == "run"
    assert workout.start_at == datetime(2026, 8, 1, 6, 0, 0, tzinfo=UTC)
    assert workout.duration_s == 300
    assert workout.distance_m is not None and workout.distance_m > 0
    assert workout.avg_hr == 135.0
    assert workout.max_hr == 150.0
    assert workout.elevation_gain_m == 4.0


def test_parse_gpx_bytes_malformed_xml_is_handled_gracefully():
    malformed = b"<gpx><trk><trkseg><trkpt lat='1' lon='2'></trkpt></trkseg"  # truncated, unclosed
    workout, warnings = parse_gpx_bytes(malformed, "broken.gpx")
    assert workout is None
    assert warnings
    assert "broken.gpx" in warnings[0]


def test_parse_gpx_bytes_no_trackpoints():
    xml = b"""<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><name>Empty</name></trk></gpx>"""
    workout, warnings = parse_gpx_bytes(xml, "empty.gpx")
    assert workout is None
    assert warnings


def test_parse_gpx_bytes_rejects_xxe_style_entity(tmp_path: Path):
    """XXE attempt: external entity referencing a local file must not be resolved
    (and must not crash); we just expect graceful handling either way."""
    secret = tmp_path / "secret.txt"
    secret.write_text("super-secret-content")
    xxe_payload = f"""<?xml version="1.0"?>
<!DOCTYPE gpx [ <!ENTITY xxe SYSTEM "{secret}"> ]>
<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><name>&xxe;</name></trk></gpx>""".encode()

    workout, warnings = parse_gpx_bytes(xxe_payload, "xxe.gpx")

    # Whatever happens, the secret file content must never appear in output, and
    # this must not raise.
    if workout is not None:
        assert workout.raw_activity_name is not None
        assert "super-secret-content" not in workout.raw_activity_name
    for w in warnings:
        assert "super-secret-content" not in w


def test_parse_gpx_file_reads_from_disk(tmp_path: Path):
    gpx_path = tmp_path / "activity.gpx"
    gpx_path.write_text(
        GPX_TEMPLATE.format(
            activity="Cycling", t0="2026-08-02T05:00:00Z", t1="2026-08-02T05:30:00Z"
        )
    )
    workout, warnings = parse_gpx_file(gpx_path)
    assert warnings == []
    assert workout is not None
    assert workout.activity_type == "cycling"


# --------------------------------------------------------------------------
# ZIP handling: malformed archives and zip-slip
# --------------------------------------------------------------------------


def test_safe_extract_zip_malformed_archive_is_handled_gracefully(tmp_path: Path):
    bad_zip = tmp_path / "corrupt.zip"
    bad_zip.write_bytes(b"PK\x03\x04not actually a valid zip stream" + b"\x00" * 20)

    extract_dir = tmp_path / "extracted"
    extracted, warnings = safe_extract_zip(bad_zip, extract_dir)

    assert extracted == []
    assert warnings


def test_safe_extract_zip_truncated_archive_is_handled_gracefully(tmp_path: Path):
    # Build a valid zip, then truncate it to simulate an incomplete download/export.
    good_zip = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip, "w") as zf:
        zf.writestr("workout.fit", b"some fit bytes")
        zf.writestr("workout.gpx", b"<gpx></gpx>")

    truncated_bytes = good_zip.read_bytes()[:20]
    truncated_zip = tmp_path / "truncated.zip"
    truncated_zip.write_bytes(truncated_bytes)

    extract_dir = tmp_path / "extracted_truncated"
    extracted, warnings = safe_extract_zip(truncated_zip, extract_dir)

    # Must not raise; either nothing extracts cleanly, or it's reported via warnings.
    assert isinstance(extracted, list)
    assert isinstance(warnings, list)


def test_safe_extract_zip_rejects_zip_slip_path_traversal(tmp_path: Path):
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../evil.txt", b"pwned")
        zf.writestr("safe.fit", b"harmless fit bytes")

    extract_dir = tmp_path / "extract_here"
    extract_dir.mkdir()

    extracted, warnings = safe_extract_zip(evil_zip, extract_dir)

    # The traversal entry must never land outside extract_dir.
    escaped_path = (tmp_path / "evil.txt").resolve()
    assert not escaped_path.exists()
    assert any("safe.fit" in str(p) for p in extracted)
    assert any("path traversal" in w or "unsafe" in w for w in warnings)


def test_safe_extract_zip_rejects_absolute_path_entry(tmp_path: Path):
    outside_target = tmp_path / "outside_target.txt"
    evil_zip = tmp_path / "evil_abs.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        # zipfile normalizes absolute paths on write, so craft the ZipInfo directly
        info = zipfile.ZipInfo(str(outside_target))
        zf.writestr(info, b"pwned")
        zf.writestr("safe.gpx", b"<gpx></gpx>")

    extract_dir = tmp_path / "extract_here_abs"
    extract_dir.mkdir()

    extracted, _warnings = safe_extract_zip(evil_zip, extract_dir)

    assert not outside_target.exists()
    assert all(
        extract_dir.resolve() in p.resolve().parents or p.resolve() == extract_dir.resolve()
        for p in extracted
    )


# --------------------------------------------------------------------------
# Cross-source (FIT + GPX) dedup within a single import batch
# --------------------------------------------------------------------------


def test_dedupe_fit_gpx_pairs_prefers_fit_for_matching_activity():
    fit_session = _make_fake_session(
        {
            "start_time": datetime(2026, 8, 1, 6, 0, 0),
            "total_timer_time": 1800.0,
            # Deliberately no total_distance here: GPX-computed distance from two
            # widely-spaced synthetic trackpoints wouldn't realistically match a
            # FIT summary distance anyway, and the matcher already skips the
            # distance check whenever either side lacks a value - start time +
            # duration closeness is enough to identify this as the same activity.
            "sport": "running",
            "avg_heart_rate": 145,
            "max_heart_rate": 170,
        }
    )
    fit_file = _make_fake_fit_file(sessions=[fit_session], records=[])
    fit_workout = extract_fit_workout(fit_file, "pair.fit")
    assert fit_workout is not None

    gpx_xml = GPX_TEMPLATE.format(
        activity="Running", t0="2026-08-01T06:00:10Z", t1="2026-08-01T06:29:50Z"
    ).encode()
    gpx_workout, gpx_warnings = parse_gpx_bytes(gpx_xml, "pair.gpx")
    assert gpx_warnings == []
    assert gpx_workout is not None

    merged = dedupe_fit_gpx_pairs([fit_workout], [gpx_workout])

    assert len(merged) == 1
    assert merged[0].source_type == "sports_tracker_fit"


def test_dedupe_fit_gpx_pairs_keeps_unmatched_gpx_standalone():
    fit_session = _make_fake_session(
        {
            "start_time": datetime(2026, 8, 1, 6, 0, 0),
            "total_timer_time": 1800.0,
            "total_distance": 5000.0,
            "sport": "running",
        }
    )
    fit_file = _make_fake_fit_file(sessions=[fit_session], records=[])
    fit_workout = extract_fit_workout(fit_file, "morning.fit")
    assert fit_workout is not None

    # A completely different, unrelated activity later the same day.
    gpx_xml = GPX_TEMPLATE.format(
        activity="Cycling", t0="2026-08-01T18:00:00Z", t1="2026-08-01T19:00:00Z"
    ).encode()
    gpx_workout, _warnings = parse_gpx_bytes(gpx_xml, "evening.gpx")
    assert gpx_workout is not None

    merged = dedupe_fit_gpx_pairs([fit_workout], [gpx_workout])

    assert len(merged) == 2
    source_types = {w.source_type for w in merged}
    assert source_types == {"sports_tracker_fit", "sports_tracker_gpx"}


# --------------------------------------------------------------------------
# End-to-end: folder and ZIP entry points
# --------------------------------------------------------------------------


def test_import_sports_tracker_folder_parses_valid_gpx_and_skips_bad_files(tmp_path: Path):
    (tmp_path / "good.gpx").write_text(
        GPX_TEMPLATE.format(
            activity="Running", t0="2026-08-03T06:00:00Z", t1="2026-08-03T06:20:00Z"
        )
    )
    (tmp_path / "corrupt.fit").write_bytes(b"not a real fit file")
    (tmp_path / "notes.txt").write_text("irrelevant junk file, should just be ignored")

    outcome = import_sports_tracker_folder(tmp_path)

    assert outcome.records_processed == 2  # good.gpx + corrupt.fit; notes.txt is not a workout file
    assert len(outcome.workouts) == 1
    assert outcome.workouts[0].source_type == "sports_tracker_gpx"
    assert any("corrupt.fit" in w for w in outcome.warnings)


def test_import_sports_tracker_zip_end_to_end(tmp_path: Path):
    zip_path = tmp_path / "export.zip"
    gpx_content = GPX_TEMPLATE.format(
        activity="Running", t0="2026-08-04T06:00:00Z", t1="2026-08-04T06:20:00Z"
    )
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Activities/run.gpx", gpx_content)
        zf.writestr("Activities/corrupt.fit", b"garbage, not a fit file")
        zf.writestr("../escape.txt", b"should never land outside extract dir")

    extract_dir = tmp_path / "extract"
    outcome = import_sports_tracker_zip(zip_path, extract_dir)

    assert len(outcome.workouts) == 1
    assert outcome.workouts[0].source_type == "sports_tracker_gpx"
    assert any("corrupt.fit" in w for w in outcome.warnings)
    assert not (tmp_path / "escape.txt").exists()


def test_import_sports_tracker_zip_handles_completely_bad_zip(tmp_path: Path):
    bad_zip = tmp_path / "not_a_zip.zip"
    bad_zip.write_bytes(b"definitely not a zip file")
    extract_dir = tmp_path / "extract_bad"

    outcome = import_sports_tracker_zip(bad_zip, extract_dir)

    assert outcome.workouts == []
    assert outcome.warnings


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
