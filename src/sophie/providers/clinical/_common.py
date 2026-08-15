"""Shared, provider-agnostic parsing helpers for the clinical import package.

Nothing here is specific to any one lab vendor. Column/key naming is
deliberately tolerant (see module docstrings of csv_import/json_import), but
values are never invented: a reference range, unit, or abnormal flag is only
ever set when the source data supplied it. See
docs/HEALTH_LOGIC_AND_SAFETY.md before changing normalization behavior.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sophie.domain.clinical_reference import canonicalize_test_name
from sophie.domain.import_types import ParsedLabResult

# Canonical field -> accepted header/key spellings (already normalized via
# _normalize_key, i.e. lowercase snake_case).
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "sample_date": ("date", "sample_date", "collection_date", "test_date", "assessed_at"),
    "test_name": ("test", "test_name", "biomarker", "analyte", "marker"),
    "value": ("value", "result", "result_value"),
    "unit": ("unit", "units"),
    "reference_low": ("reference_low", "ref_low", "low", "range_low", "low_reference"),
    "reference_high": ("reference_high", "ref_high", "high", "range_high", "high_reference"),
    "reference_range": ("reference_range", "reference", "reference_text", "range", "ref_range"),
    "abnormal_flag": ("flag", "abnormal_flag", "abnormal"),
    "notes": ("notes", "comment", "comments"),
}

_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y")

_RANGE_RE = re.compile(
    r"^\s*(-?\d+(?:[.,]\d+)?)\s*[-–‐]\s*(-?\d+(?:[.,]\d+)?)\s*$",
)

_DECIMAL_COMMA_RE = re.compile(r"^-?\d+,\d+$")


class RowError(ValueError):
    """Raised for a single malformed/unparseable row. Callers catch this,
    record a warning, and continue with the rest of the file."""


def normalize_key(key: str) -> str:
    """camelCase/Title Case/"Header Name" -> snake_case, tolerant of the
    common spellings a lab export or hand-built JSON might use."""

    key = re.sub(r"(?<!^)(?=[A-Z])", "_", key.strip())
    key = key.lower()
    key = re.sub(r"[\s\-]+", "_", key)
    key = re.sub(r"_+", "_", key)
    return key.strip("_")


def normalize_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    return {normalize_key(str(k)): v for k, v in raw_row.items() if k is not None}


def first_present(row: dict[str, Any], canonical_field: str) -> Any:
    for alias in FIELD_ALIASES[canonical_field]:
        if alias in row:
            value = row[alias]
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
    return None


def parse_float(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, int | float):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    if _DECIMAL_COMMA_RE.match(text):
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_value(raw: Any) -> tuple[float | None, str | None]:
    """Returns (value, value_text). Numeric-looking values become `value`;
    anything else (including censored results like '<0.5' or qualitative
    results like 'Positive') is preserved verbatim as `value_text` rather
    than guessed at."""

    if raw is None:
        return None, None
    text = str(raw).strip()
    if not text:
        return None, None
    if text[0] in "<>":
        return None, text
    parsed = parse_float(text)
    if parsed is None:
        return None, text
    return parsed, None


def parse_reference_range_text(text: str) -> tuple[float | None, float | None]:
    match = _RANGE_RE.match(text)
    if not match:
        return None, None
    low = parse_float(match.group(1))
    high = parse_float(match.group(2))
    return low, high


def parse_date(raw: Any) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def row_to_lab_result(raw_row: dict[str, Any]) -> ParsedLabResult:
    """Builds a ParsedLabResult from one already-tolerant row (CSV DictReader
    row, or a JSON object). Raises RowError for anything missing/unparseable
    rather than crashing or guessing at a value."""

    row = normalize_row(raw_row)

    date_raw = first_present(row, "sample_date")
    if date_raw is None:
        raise RowError("missing sample date")
    sample_date = parse_date(date_raw)
    if sample_date is None:
        raise RowError(f"unparseable sample date {date_raw!r}")

    test_name_raw = first_present(row, "test_name")
    if test_name_raw is None:
        raise RowError("missing test name")
    test_name = str(test_name_raw).strip()
    if not test_name:
        raise RowError("missing test name")
    canonical_id, category = canonicalize_test_name(test_name)

    value_raw = first_present(row, "value")
    value, value_text = parse_value(value_raw)

    unit_raw = first_present(row, "unit")
    unit = str(unit_raw).strip() if unit_raw is not None else None

    reference_low = parse_float(first_present(row, "reference_low"))
    reference_high = parse_float(first_present(row, "reference_high"))

    reference_range_raw = first_present(row, "reference_range")
    reference_text = str(reference_range_raw).strip() if reference_range_raw is not None else None

    if reference_low is None and reference_high is None and reference_text:
        reference_low, reference_high = parse_reference_range_text(reference_text)

    flag_raw = first_present(row, "abnormal_flag")
    abnormal_flag = str(flag_raw).strip() if flag_raw is not None else None

    notes_raw = first_present(row, "notes")
    notes = str(notes_raw).strip() if notes_raw is not None else None

    return ParsedLabResult(
        sample_date=sample_date,
        test_name=test_name,
        canonical_test_id=canonical_id,
        value=value,
        value_text=value_text,
        unit=unit,
        reference_low=reference_low,
        reference_high=reference_high,
        reference_text=reference_text,
        abnormal_flag=abnormal_flag,
        category=category,
        notes=notes,
    )
