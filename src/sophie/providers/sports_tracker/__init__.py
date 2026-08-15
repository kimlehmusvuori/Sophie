"""Sports Tracker import provider: historical workout data from ZIP/FIT/GPX
exports.

Pure adapter layer - takes file paths, returns plain `sophie.domain.import_types`
dataclasses. No SQLAlchemy, no Streamlit, no database/session access (see
docs/ARCHITECTURE.md layering rules). The service layer (`sophie.services.*`)
is responsible for turning the returned `ImportOutcome` into persisted rows via
`import_manifest` + repositories.

Public API:

- `import_sports_tracker_zip(zip_path, extract_dir)` - extract a Sports Tracker
  export ZIP and parse every FIT/GPX file inside it.
- `import_sports_tracker_folder(folder)` - parse FIT/GPX files already sitting in
  a folder (e.g. if the caller already extracted them, or the user points Sophie
  at an unzipped export).
- `safe_extract_zip(zip_path, extract_dir)` - lower-level zip-slip-safe
  extraction, exposed for callers that want extraction and parsing as separate
  steps.
- `parse_fit_file(path)` / `parse_gpx_file(path)` - single-file parsers, useful
  for ad-hoc inspection or lower-level pipelines.
"""

from __future__ import annotations

from .fit_parser import parse_fit_file
from .gpx_parser import parse_gpx_file
from .zip_import import (
    dedupe_fit_gpx_pairs,
    import_sports_tracker_folder,
    import_sports_tracker_zip,
    safe_extract_zip,
)

__all__ = [
    "dedupe_fit_gpx_pairs",
    "import_sports_tracker_folder",
    "import_sports_tracker_zip",
    "parse_fit_file",
    "parse_gpx_file",
    "safe_extract_zip",
]
