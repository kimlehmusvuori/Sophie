"""GPX file parsing for Sports Tracker exports.

Parses GPX (a GPS track XML format) with `lxml`, computing distance and duration
directly from trackpoint timestamps/coordinates rather than trusting any
pre-aggregated total (GPX rarely carries one). Heart rate is read from whatever
`<hr>`-named element appears inside a trackpoint's `<extensions>` block (Garmin's
TrackPointExtension namespace `gpxtpx:hr`, or Sports Tracker's own extension
namespace) - matched by local name only, so we don't need to hardcode every vendor
namespace URI.

Security: GPX is XML, so this module guards against XXE (XML External Entity)
attacks by disabling entity resolution and DTD/network loading on the parser -
see `_safe_xml_parser()`. It never raises up to its caller for malformed input;
failures are reported as warning strings and the file is skipped.

Testability: `parse_gpx_bytes()` operates on raw bytes so tests can pass synthetic
GPX strings directly (encoded) without touching the filesystem. `parse_gpx_file()`
is a thin wrapper that reads the file and delegates to it.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from lxml import etree

from sophie.domain.activity_types import normalize_free_text_activity
from sophie.domain.geo import track_distance_m
from sophie.domain.import_types import RawWorkout

SOURCE_TYPE = "sports_tracker_gpx"


def _safe_xml_parser() -> etree.XMLParser:
    """An lxml parser configured to prevent XXE: no entity resolution, no DTD
    loading, no network access, and a cap on tree size to resist decompression-bomb
    style inputs."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        huge_tree=False,
    )


def make_gpx_source_identifier(start_at: datetime, file_name: str) -> str:
    """Sports Tracker GPX exports don't carry a stable external activity ID either
    (see `fit_parser.make_fit_source_identifier` for the same tradeoff on FIT)."""
    digest_input = f"{start_at.isoformat()}|{file_name}".encode()
    return "st-gpx-" + hashlib.sha256(digest_input).hexdigest()[:24]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_child_by_local_name(element: etree._Element, name: str) -> etree._Element | None:
    for child in element.iter():
        if child is not element and _local_name(child.tag) == name:
            return child
    return None


def _parse_gpx_time(text: str) -> datetime | None:
    try:
        cleaned = text.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class _TrackPoint:
    __slots__ = ("lat", "lon", "time", "elevation_m", "hr")

    def __init__(
        self,
        lat: float | None,
        lon: float | None,
        time: datetime | None,
        elevation_m: float | None,
        hr: float | None,
    ) -> None:
        self.lat = lat
        self.lon = lon
        self.time = time
        self.elevation_m = elevation_m
        self.hr = hr


def _collect_trackpoints(root: etree._Element) -> list[_TrackPoint]:
    points: list[_TrackPoint] = []
    for trkpt in root.iter():
        if _local_name(trkpt.tag) != "trkpt":
            continue
        lat_raw = trkpt.get("lat")
        lon_raw = trkpt.get("lon")
        lat = float(lat_raw) if lat_raw is not None else None
        lon = float(lon_raw) if lon_raw is not None else None

        time_el = _find_child_by_local_name(trkpt, "time")
        time = _parse_gpx_time(time_el.text) if time_el is not None and time_el.text else None

        ele_el = _find_child_by_local_name(trkpt, "ele")
        elevation_m = None
        if ele_el is not None and ele_el.text:
            try:
                elevation_m = float(ele_el.text.strip())
            except ValueError:
                elevation_m = None

        hr: float | None = None
        for descendant in trkpt.iter():
            if _local_name(descendant.tag) == "hr" and descendant.text:
                try:
                    hr = float(descendant.text.strip())
                except ValueError:
                    hr = None
                break

        points.append(_TrackPoint(lat, lon, time, elevation_m, hr))
    return points


def _activity_label(root: etree._Element) -> str | None:
    for name in ("type", "name"):
        el = _find_child_by_local_name(root, name)
        if el is not None and el.text and el.text.strip():
            return el.text.strip()
    return None


def extract_gpx_workout(
    root: etree._Element, file_name: str, warnings: list[str]
) -> RawWorkout | None:
    """Interpret an already-parsed GPX document (`lxml` root element) into a
    `RawWorkout`. Appends a warning and returns None if there isn't enough data."""
    points = _collect_trackpoints(root)
    timed_points = [p for p in points if p.time is not None]
    if not timed_points:
        warnings.append(f"{file_name}: no timestamped trackpoints found in GPX file")
        return None

    timed_points.sort(key=lambda p: p.time)  # type: ignore[arg-type, return-value]
    start_at = timed_points[0].time
    end_at = timed_points[-1].time
    assert start_at is not None and end_at is not None  # narrowed by timed_points filter
    duration_s = int(round((end_at - start_at).total_seconds())) if end_at > start_at else None

    coords = [(p.lat, p.lon) for p in points if p.lat is not None and p.lon is not None]
    distance_m = track_distance_m(coords) if len(coords) >= 2 else None

    hr_values = [p.hr for p in points if p.hr is not None]
    avg_hr = (sum(hr_values) / len(hr_values)) if hr_values else None
    max_hr = max(hr_values) if hr_values else None

    elevations = [p.elevation_m for p in points if p.elevation_m is not None]
    elevation_gain_m = None
    if len(elevations) >= 2:
        elevation_gain_m = sum(
            max(0.0, b - a) for a, b in zip(elevations, elevations[1:], strict=False)
        )

    raw_label = _activity_label(root)

    return RawWorkout(
        source_type=SOURCE_TYPE,
        source_identifier=make_gpx_source_identifier(start_at, file_name),
        activity_type=normalize_free_text_activity(raw_label),
        start_at=start_at,
        end_at=end_at,
        duration_s=duration_s,
        distance_m=distance_m,
        avg_hr=avg_hr,
        max_hr=max_hr,
        elevation_gain_m=elevation_gain_m,
        raw_activity_name=raw_label,
    )


def parse_gpx_bytes(data: bytes, file_name: str) -> tuple[RawWorkout | None, list[str]]:
    """Exception-safe: parse GPX content already read into memory. Returns
    `(workout_or_none, warnings)` - never raises for malformed XML."""
    warnings: list[str] = []
    parser = _safe_xml_parser()
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError as exc:
        warnings.append(f"{file_name}: malformed GPX XML ({exc})")
        return None, warnings
    except Exception as exc:  # noqa: BLE001 - defensive: never let a bad file crash the import
        warnings.append(f"{file_name}: unexpected error parsing GPX file ({exc})")
        return None, warnings

    try:
        workout = extract_gpx_workout(root, file_name, warnings)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{file_name}: unexpected error interpreting GPX file ({exc})")
        return None, warnings
    return workout, warnings


def parse_gpx_file(path: str | Path) -> tuple[RawWorkout | None, list[str]]:
    """Exception-safe entry point: parse a single `.gpx` file on disk."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, [f"{path.name}: could not read GPX file ({exc})"]
    return parse_gpx_bytes(data, path.name)
