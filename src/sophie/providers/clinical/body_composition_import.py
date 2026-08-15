"""CSV/JSON import for provider-independent body composition assessments
(DEXA, bioimpedance, calipers, etc.). Tolerant column/key naming, similar in
spirit to the lab result importers.

This module never compares or normalizes across different `method` values
(e.g. DEXA vs bioimpedance) — that comparability judgement belongs to a
service/UI layer, not this provider. It also never invents a measurement
method: if the source data does not supply one, "unknown" is used verbatim
as a data-quality label, not a guess at technique.

This module must never import sqlalchemy/streamlit or call an LLM/network
API — it returns plain dataclasses; a service layer persists them.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sophie.domain.import_types import ParsedBodyComposition

from ._common import RowError, normalize_row, parse_date, parse_float

_ALIASES: dict[str, tuple[str, ...]] = {
    "assessed_at": ("assessed_at", "date", "assessment_date"),
    "method": ("method", "measurement_method"),
    "provider": ("provider",),
    "weight_kg": ("weight_kg", "weight"),
    "body_fat_pct": ("body_fat_pct", "bodyfat", "body_fat", "body_fat_percentage"),
    "lean_mass_kg": ("lean_mass_kg", "lean_mass"),
    "visceral_metric": ("visceral_metric", "visceral"),
    "segmental": ("segmental",),
    "notes": ("notes", "comment", "comments"),
}


def _first(row: dict[str, Any], field: str) -> Any:
    for alias in _ALIASES[field]:
        if alias in row:
            value = row[alias]
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
    return None


def _row_to_body_composition(raw_row: dict[str, Any]) -> ParsedBodyComposition:
    row = normalize_row(raw_row)

    date_raw = _first(row, "assessed_at")
    if date_raw is None:
        raise RowError("missing assessment date")
    assessed_at = parse_date(date_raw)
    if assessed_at is None:
        raise RowError(f"unparseable assessment date {date_raw!r}")

    method_raw = _first(row, "method")
    method = str(method_raw).strip() if method_raw is not None else "unknown"

    provider_raw = _first(row, "provider")
    provider = str(provider_raw).strip() if provider_raw is not None else None

    weight_kg = parse_float(_first(row, "weight_kg"))
    body_fat_pct = parse_float(_first(row, "body_fat_pct"))
    lean_mass_kg = parse_float(_first(row, "lean_mass_kg"))
    visceral_metric = parse_float(_first(row, "visceral_metric"))

    segmental_raw = _first(row, "segmental")
    segmental: dict[str, Any] | None
    if isinstance(segmental_raw, dict):
        segmental = segmental_raw
    elif isinstance(segmental_raw, str):
        try:
            parsed = json.loads(segmental_raw)
        except json.JSONDecodeError:
            segmental = None
        else:
            segmental = parsed if isinstance(parsed, dict) else None
    else:
        segmental = None

    notes_raw = _first(row, "notes")
    notes = str(notes_raw).strip() if notes_raw is not None else None

    return ParsedBodyComposition(
        assessed_at=assessed_at,
        method=method,
        provider=provider,
        weight_kg=weight_kg,
        body_fat_pct=body_fat_pct,
        lean_mass_kg=lean_mass_kg,
        segmental=segmental,
        visceral_metric=visceral_metric,
        notes=notes,
    )


def import_body_composition_csv(path: str | Path) -> list[ParsedBodyComposition]:
    file_path = Path(path)
    results: list[ParsedBodyComposition] = []
    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return results
        for raw_row in reader:
            if raw_row is None or all(v in (None, "") for v in raw_row.values()):
                continue
            try:
                results.append(_row_to_body_composition(raw_row))
            except RowError:
                continue
    return results


def import_body_composition_json(path: str | Path) -> list[ParsedBodyComposition]:
    file_path = Path(path)
    with file_path.open(encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError:
            return []

    rows: list[Any]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        list_keys = ("results", "assessments")
        rows = next(
            (payload[key] for key in list_keys if isinstance(payload.get(key), list)),
            [],
        )
    else:
        rows = []

    results: list[ParsedBodyComposition] = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            continue
        try:
            results.append(_row_to_body_composition(raw_row))
        except RowError:
            continue
    return results
