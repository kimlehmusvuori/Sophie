"""FIT file parsing for Sports Tracker exports.

Uses `fitparse` to read `session` (and, as a fallback, `record`) messages and turns
them into a `sophie.domain.import_types.RawWorkout`. This module never raises up to
its caller for malformed input - parsing failures are reported as warning strings and
the file is skipped.

Source identifier: Sports Tracker FIT exports don't carry a clean, stable external
activity ID (no server-assigned UUID field is reliably populated), so we derive one
deterministically from `(start_time, raw sport string, file name)`. This is stable
across re-imports of the same file, but changes if the user renames the file or if
Sports Tracker ever re-exports with a different start-time rounding. That's an
accepted tradeoff for a provider-local fingerprint; it is not used as the sole
cross-source dedup key (see `zip_import.py` for start-time/duration/distance based
FIT+GPX pairing, and the future canonical_workout layer for cross-provider dedup).

Testability: `extract_fit_workout()` takes anything exposing a fitparse-like
`get_messages(name)` method, so tests can inject a hand-built fake object (or a
`unittest.mock.MagicMock`) instead of a real binary FIT file. `parse_fit_file()` is
the outer, exception-safe entry point that constructs a real `fitparse.FitFile`.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from fitparse import FitFile
from fitparse.utils import FitParseError

from sophie.domain.activity_types import normalize_fit_sport
from sophie.domain.import_types import RawWorkout

logger = logging.getLogger(__name__)

SOURCE_TYPE = "sports_tracker_fit"


class FitMessageLike(Protocol):
    """Minimal shape of a fitparse `DataMessage` that we depend on."""

    def get_value(self, field_name: str) -> Any: ...


class FitFileLike(Protocol):
    """Minimal shape of a `fitparse.FitFile` that we depend on - lets tests inject a
    fake/mock instead of a real binary FIT file."""

    def get_messages(self, name: str | None = None) -> Any: ...


def make_fit_source_identifier(start_at: datetime, sport: str | None, file_name: str) -> str:
    """Derive a stable-ish identifier for a FIT-sourced workout. See module docstring."""
    digest_input = f"{start_at.isoformat()}|{sport or ''}|{file_name}".encode()
    return "st-fit-" + hashlib.sha256(digest_input).hexdigest()[:24]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _first(iterable: Any) -> Any | None:
    for item in iterable:
        return item
    return None


def _workout_from_session(session: FitMessageLike, file_name: str) -> RawWorkout | None:
    start_time = session.get_value("start_time")
    if start_time is None:
        return None
    start_at = _as_utc(start_time)

    duration_s: int | None = None
    timer_time = session.get_value("total_timer_time")
    elapsed_time = session.get_value("total_elapsed_time")
    duration_source = timer_time if timer_time is not None else elapsed_time
    if duration_source is not None:
        duration_s = int(round(float(duration_source)))

    end_at = start_at + timedelta(seconds=duration_s) if duration_s else None

    distance_m = session.get_value("total_distance")
    sport_raw = session.get_value("sport")
    sub_sport_raw = session.get_value("sub_sport")
    avg_hr = session.get_value("avg_heart_rate")
    max_hr = session.get_value("max_heart_rate")
    elevation_gain_m = session.get_value("total_ascent")

    raw_name = sport_raw or sub_sport_raw

    return RawWorkout(
        source_type=SOURCE_TYPE,
        source_identifier=make_fit_source_identifier(start_at, sport_raw, file_name),
        activity_type=normalize_fit_sport(sport_raw),
        start_at=start_at,
        end_at=end_at,
        duration_s=duration_s,
        distance_m=float(distance_m) if distance_m is not None else None,
        avg_hr=float(avg_hr) if avg_hr is not None else None,
        max_hr=float(max_hr) if max_hr is not None else None,
        elevation_gain_m=float(elevation_gain_m) if elevation_gain_m is not None else None,
        raw_activity_name=str(raw_name) if raw_name else None,
    )


def _workout_from_records(records: list[FitMessageLike], file_name: str) -> RawWorkout | None:
    """Fallback for FIT files that lack a `session` summary message: reconstruct a
    coarse summary from raw `record` messages (one per sampled instant)."""
    timestamps: list[datetime] = []
    hr_values: list[float] = []
    altitudes: list[float] = []
    distances: list[float] = []

    for record in records:
        ts = record.get_value("timestamp")
        if ts is not None:
            timestamps.append(_as_utc(ts))
        hr = record.get_value("heart_rate")
        if hr is not None:
            hr_values.append(float(hr))
        alt = record.get_value("altitude")
        if alt is not None:
            altitudes.append(float(alt))
        dist = record.get_value("distance")
        if dist is not None:
            distances.append(float(dist))

    if not timestamps:
        return None

    start_at = min(timestamps)
    end_at = max(timestamps)
    duration_s = int(round((end_at - start_at).total_seconds())) if end_at > start_at else None

    elevation_gain_m = None
    if len(altitudes) >= 2:
        gain = sum(max(0.0, b - a) for a, b in zip(altitudes, altitudes[1:], strict=False))
        elevation_gain_m = gain

    distance_m = max(distances) if distances else None

    return RawWorkout(
        source_type=SOURCE_TYPE,
        source_identifier=make_fit_source_identifier(start_at, None, file_name),
        activity_type="other",
        start_at=start_at,
        end_at=end_at,
        duration_s=duration_s,
        distance_m=distance_m,
        avg_hr=(sum(hr_values) / len(hr_values)) if hr_values else None,
        max_hr=max(hr_values) if hr_values else None,
        elevation_gain_m=elevation_gain_m,
        raw_activity_name=None,
    )


def extract_fit_workout(fit_file: FitFileLike, file_name: str) -> RawWorkout | None:
    """Interpret an already-open FIT file (or a fake/mock exposing `get_messages`)
    into a `RawWorkout`. Returns None if there isn't enough data to build one."""
    session = _first(fit_file.get_messages("session"))
    if session is not None:
        workout = _workout_from_session(session, file_name)
        if workout is not None:
            return workout

    records = list(fit_file.get_messages("record"))
    if records:
        return _workout_from_records(records, file_name)

    return None


def parse_fit_file(path: str | Path, warnings: list[str] | None = None) -> RawWorkout | None:
    """Exception-safe entry point: parse a single `.fit` file on disk. Any parsing
    failure (corrupt file, unexpected structure, etc.) is appended to `warnings`
    (a new list is created and discarded by the caller if none is passed) and the
    function returns None instead of raising."""
    if warnings is None:
        warnings = []
    path = Path(path)
    try:
        fit_file = FitFile(str(path))
        workout = extract_fit_workout(fit_file, path.name)
        if workout is None:
            warnings.append(f"{path.name}: no usable session/record data found in FIT file")
        return workout
    except FitParseError as exc:
        warnings.append(f"{path.name}: malformed FIT file ({exc})")
        return None
    except OSError as exc:
        warnings.append(f"{path.name}: could not read FIT file ({exc})")
        return None
    except Exception as exc:  # noqa: BLE001 - defensive: never let a bad file crash the import
        warnings.append(f"{path.name}: unexpected error parsing FIT file ({exc})")
        return None
