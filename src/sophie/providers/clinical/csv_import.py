"""CSV import for provider-independent clinical lab results.

Accepts a reasonably flexible column scheme (see FIELD_ALIASES in
_common.py): "date"/"sample_date", "test"/"test_name"/"biomarker",
"value"/"result", "unit", "reference_low"/"ref_low"/"low",
"reference_high"/"ref_high"/"high", a combined "reference_range"/"reference"
text column, and "flag"/"abnormal_flag". Never invents a unit, reference
range, or abnormal flag that the source file did not supply — see
docs/HEALTH_LOGIC_AND_SAFETY.md.

This module must never import sqlalchemy/streamlit or call an LLM/network
API — it returns plain dataclasses; a service layer persists them.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sophie.domain.import_types import ClinicalImportOutcome

from ._common import RowError, row_to_lab_result


def import_lab_results_csv(path: str | Path) -> ClinicalImportOutcome:
    """Imports lab results from a CSV file the user pointed Sophie at
    directly (trusted structured data), so requires_confirmation is False."""

    file_path = Path(path)
    results = []
    warnings: list[str] = []

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return ClinicalImportOutcome(
                warnings=["CSV file has no header row; no results imported."],
            )
        for line_no, raw_row in enumerate(reader, start=2):
            if raw_row is None or all(v in (None, "") for v in raw_row.values()):
                continue
            try:
                results.append(row_to_lab_result(raw_row))
            except RowError as exc:
                warnings.append(f"Row {line_no}: {exc}, skipped.")
                continue

    return ClinicalImportOutcome(results=results, requires_confirmation=False, warnings=warnings)
