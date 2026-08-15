"""JSON import for provider-independent clinical lab results.

Accepts either a top-level list of result objects, or a dict with a
"results"/"labs" key holding that list. Field names may be camelCase or
snake_case (same tolerant aliasing as csv_import — see _common.py). Same
normalization/safety rules as the CSV importer: never invents a unit,
reference range, or abnormal flag.

This module must never import sqlalchemy/streamlit or call an LLM/network
API — it returns plain dataclasses; a service layer persists them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sophie.domain.import_types import ClinicalImportOutcome

from ._common import RowError, row_to_lab_result

_LIST_KEYS = ("results", "labs")


_UNRECOGNIZED_SHAPE_WARNING = (
    "JSON file did not contain a top-level list, or a 'results'/'labs' list; no results imported."
)


def import_lab_results_json(path: str | Path) -> ClinicalImportOutcome:
    """Imports lab results from a JSON file the user pointed Sophie at
    directly (trusted structured data), so requires_confirmation is False."""

    file_path = Path(path)
    with file_path.open(encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            return ClinicalImportOutcome(warnings=[f"Could not parse JSON file: {exc}"])

    rows: list[Any]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next(
            (payload[key] for key in _LIST_KEYS if isinstance(payload.get(key), list)),
            [],
        )
        if not rows and not any(isinstance(payload.get(key), list) for key in _LIST_KEYS):
            return ClinicalImportOutcome(warnings=[_UNRECOGNIZED_SHAPE_WARNING])
    else:
        return ClinicalImportOutcome(warnings=[_UNRECOGNIZED_SHAPE_WARNING])

    results = []
    warnings: list[str] = []
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, dict):
            warnings.append(f"Item {index}: not an object, skipped.")
            continue
        try:
            results.append(row_to_lab_result(raw_row))
        except RowError as exc:
            warnings.append(f"Item {index}: {exc}, skipped.")
            continue

    return ClinicalImportOutcome(results=results, requires_confirmation=False, warnings=warnings)
