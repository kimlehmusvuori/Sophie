"""Streaming Apple Health export.xml parser. Never loads the full file into
memory — uses lxml.etree.iterparse with element-clearing, and safe parser
settings (no external entity resolution, no network, no DTD loading) to
guard against XXE. See docs/PRODUCT_SPEC.md §9-11.

Simplifying assumptions (documented, not silently made):
- A night's sleep is attributed to the calendar date of its *end* timestamp
  (the wake-up date), which is the common daily-summary convention.
- Workout elevation gain is not extracted from export.xml (Apple typically
  stores that in the separate workout-routes GPX files, out of scope here);
  it is left as None rather than guessed at.
- <Correlation>/<ClinicalRecord> elements (e.g. blood pressure groupings)
  are not parsed in this build — a documented, scoped-out gap, not a bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from lxml import etree

from sophie.domain.activity_types import normalize_apple_health_activity
from sophie.domain.apple_health_mapping import (
    CATEGORY_TYPE_MINDFULNESS,
    CATEGORY_TYPE_SLEEP,
    QUANTITY_TYPE_MAP,
    SLEEP_ASLEEP_VALUES,
    friendly_name_for,
)
from sophie.domain.import_types import (
    DailyQuantitySample,
    ImportOutcome,
    MetricCatalogEntry,
    RawWorkout,
)
from sophie.providers.apple_health.errors import AppleHealthImportError

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S %z",)


def _parse_apple_date(raw: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


@dataclass
class _CatalogAccumulator:
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    count: int = 0
    unit: str | None = None


@dataclass
class _DailyAccumulator:
    sums: dict[str, dict[str, float]] = field(default_factory=dict)
    lists: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    lasts: dict[str, dict[str, tuple[datetime, float]]] = field(default_factory=dict)

    def add(self, field_name: str, day: str, value: float, aggregation: str, at: datetime) -> None:
        if aggregation == "sum":
            sum_bucket = self.sums.setdefault(field_name, {})
            sum_bucket[day] = sum_bucket.get(day, 0.0) + value
        elif aggregation == "avg":
            list_bucket = self.lists.setdefault(field_name, {})
            list_bucket.setdefault(day, []).append(value)
        elif aggregation == "last":
            last_bucket = self.lasts.setdefault(field_name, {})
            existing = last_bucket.get(day)
            if existing is None or at >= existing[0]:
                last_bucket[day] = (at, value)

    def to_samples(self) -> list[DailyQuantitySample]:
        samples: list[DailyQuantitySample] = []
        for field_name, sum_by_day in self.sums.items():
            for day, total in sum_by_day.items():
                samples.append(
                    DailyQuantitySample(day=_iso_to_date(day), field=field_name, value=total)
                )
        for field_name, list_by_day in self.lists.items():
            for day, values in list_by_day.items():
                samples.append(
                    DailyQuantitySample(
                        day=_iso_to_date(day), field=field_name, value=sum(values) / len(values)
                    )
                )
        for field_name, last_by_day in self.lasts.items():
            for day, (_, last_value) in last_by_day.items():
                samples.append(
                    DailyQuantitySample(day=_iso_to_date(day), field=field_name, value=last_value)
                )
        return samples


def _iso_to_date(day: str):  # -> date
    return datetime.strptime(day, "%Y-%m-%d").date()


def _handle_quantity_record(
    elem, catalog: dict[str, _CatalogAccumulator], daily: _DailyAccumulator
) -> None:
    record_type = elem.get("type")
    if not record_type:
        return
    start_raw = elem.get("startDate")
    start = _parse_apple_date(start_raw) if start_raw else None
    unit = elem.get("unit")

    acc = catalog.setdefault(record_type, _CatalogAccumulator())
    acc.count += 1
    acc.unit = acc.unit or unit
    if start is not None:
        if acc.first_seen_at is None or start < acc.first_seen_at:
            acc.first_seen_at = start
        if acc.last_seen_at is None or start > acc.last_seen_at:
            acc.last_seen_at = start

    mapping = QUANTITY_TYPE_MAP.get(record_type)
    if mapping is None or mapping.field is None or start is None:
        return

    value_raw = elem.get("value")
    if value_raw is None:
        return
    try:
        value = float(value_raw)
    except ValueError:
        return

    if mapping.unit_converters and unit in mapping.unit_converters:
        value = mapping.unit_converters[unit](value)

    day_key = start.astimezone(UTC).date().isoformat()
    daily.add(mapping.field, day_key, value, mapping.aggregation, start)


def _handle_category_record(
    elem, catalog: dict[str, _CatalogAccumulator], daily: _DailyAccumulator
) -> None:
    record_type = elem.get("type")
    if record_type not in (CATEGORY_TYPE_SLEEP, CATEGORY_TYPE_MINDFULNESS):
        return
    start_raw, end_raw = elem.get("startDate"), elem.get("endDate")
    start = _parse_apple_date(start_raw) if start_raw else None
    end = _parse_apple_date(end_raw) if end_raw else None

    acc = catalog.setdefault(record_type, _CatalogAccumulator())
    acc.count += 1
    if start is not None:
        if acc.first_seen_at is None or start < acc.first_seen_at:
            acc.first_seen_at = start
        if acc.last_seen_at is None or start > acc.last_seen_at:
            acc.last_seen_at = start

    if start is None or end is None:
        return
    duration_min = (end - start).total_seconds() / 60.0
    if duration_min <= 0:
        return

    if record_type == CATEGORY_TYPE_SLEEP:
        value = elem.get("value")
        if value in SLEEP_ASLEEP_VALUES:
            wake_day = end.astimezone(UTC).date().isoformat()
            daily.add("sleep_minutes", wake_day, duration_min, "sum", end)
    elif record_type == CATEGORY_TYPE_MINDFULNESS:
        day_key = start.astimezone(UTC).date().isoformat()
        daily.add("mindful_minutes", day_key, duration_min, "sum", start)


_DURATION_UNIT_TO_SECONDS = {"min": 60.0, "sec": 1.0, "hr": 3600.0}
_DISTANCE_UNIT_TO_M = {"km": 1000.0, "mi": 1609.344, "m": 1.0}


def _handle_workout(elem) -> RawWorkout | None:
    activity_type_raw = elem.get("workoutActivityType", "")
    start_raw, end_raw = elem.get("startDate"), elem.get("endDate")
    start = _parse_apple_date(start_raw) if start_raw else None
    end = _parse_apple_date(end_raw) if end_raw else None
    if start is None:
        return None

    duration_s: float | None = None
    duration_attr = elem.get("duration")
    if duration_attr is not None:
        try:
            duration_s = float(duration_attr) * _DURATION_UNIT_TO_SECONDS.get(
                elem.get("durationUnit", "min"), 60.0
            )
        except ValueError:
            duration_s = None
    elif end is not None:
        duration_s = (end - start).total_seconds()

    distance_m: float | None = None
    total_distance = elem.get("totalDistance")
    if total_distance is not None:
        try:
            distance_m = float(total_distance) * _DISTANCE_UNIT_TO_M.get(
                elem.get("totalDistanceUnit", "km"), 1000.0
            )
        except ValueError:
            distance_m = None

    avg_hr = max_hr = None
    for stat in elem.findall("WorkoutStatistics"):
        stat_type = stat.get("type")
        if stat_type == "HKQuantityTypeIdentifierHeartRate":
            avg_hr = _safe_float(stat.get("average"))
            max_hr = _safe_float(stat.get("maximum"))
        elif stat_type == "HKQuantityTypeIdentifierDistanceWalkingRunning" and distance_m is None:
            unit = stat.get("unit", "km")
            distance_m = _safe_float(stat.get("sum"))
            if distance_m is not None:
                distance_m *= _DISTANCE_UNIT_TO_M.get(unit, 1000.0)

    return RawWorkout(
        source_type="apple_health",
        source_identifier=elem.get("sourceName"),
        activity_type=normalize_apple_health_activity(activity_type_raw),
        start_at=start.astimezone(UTC),
        end_at=end.astimezone(UTC) if end else None,
        duration_s=int(duration_s) if duration_s is not None else None,
        distance_m=distance_m,
        avg_hr=avg_hr,
        max_hr=max_hr,
        elevation_gain_m=None,
        raw_activity_name=activity_type_raw,
    )


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_apple_health_export(xml_path: str | Path) -> ImportOutcome:
    """Streams export.xml and returns an ImportOutcome. Raises
    AppleHealthImportError only if parsing fails before any record could be
    read; a mid-stream failure after some records is reported back as a
    warning on a partial result, not a crash."""

    xml_path = Path(xml_path)
    catalog: dict[str, _CatalogAccumulator] = {}
    daily = _DailyAccumulator()
    workouts: list[RawWorkout] = []
    warnings: list[str] = []
    records_processed = 0

    try:
        context = etree.iterparse(
            str(xml_path),
            events=("end",),
            tag=("Record", "Workout"),
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
            huge_tree=True,
            recover=False,
        )
        for _, elem in context:
            tag = elem.tag
            try:
                if tag == "Record":
                    record_type = elem.get("type", "")
                    if record_type.startswith("HKCategoryTypeIdentifier"):
                        _handle_category_record(elem, catalog, daily)
                    else:
                        _handle_quantity_record(elem, catalog, daily)
                    records_processed += 1
                elif tag == "Workout":
                    workout = _handle_workout(elem)
                    if workout is not None:
                        workouts.append(workout)
                    records_processed += 1
            except Exception as exc:  # noqa: BLE001 - one bad record must not abort the import
                warnings.append(f"Skipped a malformed {tag} element: {exc}")
            finally:
                elem.clear()
                while elem.getprevious() is not None:
                    parent = elem.getparent()
                    if parent is None:
                        break
                    del parent[0]
    except etree.XMLSyntaxError as exc:
        if records_processed == 0:
            raise AppleHealthImportError(
                "The export.xml file could not be parsed — it does not appear to be valid XML."
            ) from exc
        warnings.append(
            f"The export appears truncated or malformed after {records_processed} records; "
            "imported everything readable up to that point."
        )

    catalog_entries = [
        MetricCatalogEntry(
            record_type=record_type,
            friendly_name=friendly_name_for(record_type),
            first_seen_at=acc.first_seen_at,
            last_seen_at=acc.last_seen_at,
            count=acc.count,
            unit=acc.unit,
            status=_status_for(record_type),
        )
        for record_type, acc in catalog.items()
    ]

    return ImportOutcome(
        workouts=workouts,
        daily_samples=daily.to_samples(),
        catalog_entries=catalog_entries,
        warnings=warnings,
        records_processed=records_processed,
    )


def _status_for(record_type: str) -> str:
    mapping = QUANTITY_TYPE_MAP.get(record_type)
    if mapping is not None:
        return mapping.status
    if record_type in (CATEGORY_TYPE_SLEEP, CATEGORY_TYPE_MINDFULNESS):
        return "actively_used"
    return "recognized_unused"
