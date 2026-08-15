"""Provider-independent clinical laboratory + body composition import.

Deliberately vendor-agnostic: the user's real data happens to come from a
single occupational-health provider, but nothing here is specific to any lab
vendor — provider name is treated as free text on the parsed records.

This package must never import sqlalchemy/streamlit or call an LLM/network
API. It returns plain dataclasses (see sophie.domain.import_types); a
service layer (not this package) is responsible for persistence.
"""

from __future__ import annotations

from pathlib import Path

from sophie.domain.import_types import ClinicalImportOutcome

from .body_composition_import import (
    import_body_composition_csv,
    import_body_composition_json,
)
from .csv_import import import_lab_results_csv
from .json_import import import_lab_results_json
from .pdf_import import import_lab_results_pdf

__all__ = [
    "import_lab_results_csv",
    "import_lab_results_json",
    "import_lab_results_pdf",
    "import_body_composition_csv",
    "import_body_composition_json",
    "detect_and_import_clinical_file",
]


def detect_and_import_clinical_file(path: str | Path) -> ClinicalImportOutcome:
    """Convenience dispatcher: picks the lab-result importer by file
    extension. Body composition files are not part of this dispatch since
    they return a different shape (list[ParsedBodyComposition]) — call
    import_body_composition_csv/json directly for those."""

    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return import_lab_results_csv(file_path)
    if suffix == ".json":
        return import_lab_results_json(file_path)
    if suffix == ".pdf":
        return import_lab_results_pdf(file_path)
    return ClinicalImportOutcome(
        warnings=[f"Unsupported clinical import file type: {suffix or '(none)'}"],
    )
