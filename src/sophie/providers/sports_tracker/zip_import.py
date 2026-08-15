"""Top-level Sports Tracker import entry points: ZIP extraction (with zip-slip
protection) plus folder-level FIT+GPX parsing and cross-format dedup.

Privacy/retention note (see docs/PRIVACY.md): this provider never persists the raw
ZIP or its extracted contents itself. `import_sports_tracker_zip()` extracts into a
caller-supplied temp directory and returns it via `ImportOutcome`-adjacent metadata
only insofar as the caller passed it in; the caller (a future
`sophie.services.import_pipeline`) owns creating a temp dir (e.g.
`tempfile.mkdtemp()`) and deleting it once done - this module does not delete
`extract_dir` itself, so callers can inspect it first if useful, but must clean it
up afterward.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from sophie.domain.import_types import ImportOutcome, RawWorkout

from .fit_parser import parse_fit_file
from .gpx_parser import parse_gpx_file

# Matching tolerances for treating a FIT workout and a GPX workout in the same
# import batch as the *same* real-world activity (see module docstring in
# fit_parser.py / gpx_parser.py re: neither format has a reliable shared external
# ID, so we match on closeness instead).
_PAIR_TIME_TOLERANCE_S = 120
_PAIR_MIN_DURATION_TOLERANCE_S = 60
_PAIR_MIN_DISTANCE_TOLERANCE_M = 200.0
_PAIR_RELATIVE_TOLERANCE = 0.1


def safe_extract_zip(zip_path: str | Path, extract_dir: str | Path) -> tuple[list[Path], list[str]]:
    """Extract `zip_path` into `extract_dir`, guarding against:

    - zip-slip / path traversal: any entry whose resolved path would land outside
      `extract_dir` (via `../` components, an absolute path, or a symlink-like
      trick) is rejected and skipped, not extracted.
    - malformed/truncated archives: `BadZipFile` (and per-member extraction errors)
      are caught; whatever members *did* extract cleanly are kept, and a warning is
      recorded rather than raising.

    Returns `(extracted_file_paths, warnings)`. Never raises for a bad/partial ZIP.
    """
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_dir_resolved = extract_dir.resolve()

    extracted: list[Path] = []
    warnings: list[str] = []

    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        warnings.append(f"could not open ZIP archive ({exc})")
        return extracted, warnings

    with zf:
        try:
            infolist = zf.infolist()
        except (zipfile.BadZipFile, OSError) as exc:
            warnings.append(f"could not read ZIP archive contents ({exc})")
            return extracted, warnings

        for info in infolist:
            if info.is_dir():
                continue

            member_name = info.filename
            destination = (extract_dir / member_name).resolve()
            if (
                destination != extract_dir_resolved
                and extract_dir_resolved not in destination.parents
            ):
                warnings.append(f"rejected unsafe ZIP entry (path traversal): {member_name!r}")
                continue

            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, open(destination, "wb") as target:
                    target.write(source.read())
            except (zipfile.BadZipFile, OSError, ValueError) as exc:
                warnings.append(f"could not extract ZIP entry {member_name!r} ({exc})")
                continue

            extracted.append(destination)

    return extracted, warnings


def _is_same_activity(a: RawWorkout, b: RawWorkout) -> bool:
    """Heuristic match for "same real-world activity, exported twice" (once as FIT,
    once as GPX) within a single Sports Tracker import batch. Not used for
    cross-provider dedup (e.g. against Apple Health) - that lives in the shared
    canonical_workout layer."""
    if abs((a.start_at - b.start_at).total_seconds()) > _PAIR_TIME_TOLERANCE_S:
        return False

    if a.duration_s is not None and b.duration_s is not None:
        tolerance = max(
            _PAIR_MIN_DURATION_TOLERANCE_S,
            _PAIR_RELATIVE_TOLERANCE * max(a.duration_s, b.duration_s),
        )
        if abs(a.duration_s - b.duration_s) > tolerance:
            return False

    if a.distance_m is not None and b.distance_m is not None:
        tolerance = max(
            _PAIR_MIN_DISTANCE_TOLERANCE_M,
            _PAIR_RELATIVE_TOLERANCE * max(a.distance_m, b.distance_m),
        )
        if abs(a.distance_m - b.distance_m) > tolerance:
            return False

    return True


def dedupe_fit_gpx_pairs(
    fit_workouts: list[RawWorkout], gpx_workouts: list[RawWorkout]
) -> list[RawWorkout]:
    """Merge a batch's FIT and GPX workouts, preferring the FIT summary (better
    HR/metadata quality typically) whenever a GPX workout appears to represent the
    same activity as one already covered by a FIT file. Unmatched GPX workouts are
    kept standalone (`source_type == "sports_tracker_gpx"`)."""
    result: list[RawWorkout] = list(fit_workouts)
    for gpx_workout in gpx_workouts:
        if any(_is_same_activity(gpx_workout, fit_workout) for fit_workout in fit_workouts):
            continue  # superseded by a paired FIT file - drop the redundant GPX entry
        result.append(gpx_workout)
    return result


def import_sports_tracker_folder(folder: str | Path) -> ImportOutcome:
    """Parse every `.fit` and `.gpx` file found (recursively) under `folder` and
    return a combined, deduped `ImportOutcome`. Never raises for individual bad
    files - failures become entries in `ImportOutcome.warnings`."""
    folder = Path(folder)
    outcome = ImportOutcome()

    fit_paths = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".fit")
    gpx_paths = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".gpx")

    fit_workouts: list[RawWorkout] = []
    for fit_path in fit_paths:
        outcome.records_processed += 1
        workout = parse_fit_file(fit_path, outcome.warnings)
        if workout is not None:
            fit_workouts.append(workout)

    gpx_workouts: list[RawWorkout] = []
    for gpx_path in gpx_paths:
        outcome.records_processed += 1
        workout, file_warnings = parse_gpx_file(gpx_path)
        outcome.warnings.extend(file_warnings)
        if workout is not None:
            gpx_workouts.append(workout)

    outcome.workouts = dedupe_fit_gpx_pairs(fit_workouts, gpx_workouts)
    return outcome


def import_sports_tracker_zip(zip_path: str | Path, extract_dir: str | Path) -> ImportOutcome:
    """Top-level provider entry point for a Sports Tracker export ZIP.

    Extracts `zip_path` into `extract_dir` (created if needed) with zip-slip
    protection, then parses every `.fit`/`.gpx` file found, applying FIT+GPX pair
    dedup within the batch. Malformed archives, malformed members, and malformed
    FIT/GPX files are all reported as warnings rather than raised.

    Per docs/PRIVACY.md, Sophie never retains raw Sports Tracker files: this
    function does not delete `extract_dir` itself (so a caller can inspect it, or
    reuse the same dir across a multi-zip import), but the caller is responsible
    for removing it once the returned `ImportOutcome` has been persisted, e.g.:

        with tempfile.TemporaryDirectory() as tmp:
            outcome = import_sports_tracker_zip(zip_path, tmp)
            # ... hand outcome to the import pipeline/service layer ...
        # tmp and its contents are gone here
    """
    extract_dir = Path(extract_dir)
    extracted_paths, zip_warnings = safe_extract_zip(zip_path, extract_dir)
    outcome = import_sports_tracker_folder(extract_dir)
    outcome.warnings = zip_warnings + outcome.warnings
    if not extracted_paths and not zip_warnings:
        outcome.warnings.append("ZIP archive contained no extractable files")
    return outcome
