"""Safe extraction of an Apple Health export ZIP. Guards against zip-slip
path traversal, malformed/incomplete archives, and missing export.xml. The
original ZIP is never modified or persisted — callers are responsible for
cleaning up the temp extraction directory (use as a context manager)."""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sophie.providers.apple_health.errors import AppleHealthImportError

_EXPORT_XML_CANDIDATES = ("apple_health_export/export.xml", "export.xml")


def _is_safe_member(name: str, dest_root: Path) -> bool:
    if name.startswith("/") or name.startswith("\\"):
        return False
    candidate = (dest_root / name).resolve()
    try:
        candidate.relative_to(dest_root.resolve())
    except ValueError:
        return False
    return True


def _safe_extract_all(zf: zipfile.ZipFile, dest_root: Path) -> list[str]:
    extracted: list[str] = []
    for member in zf.infolist():
        if member.is_dir():
            continue
        if not _is_safe_member(member.filename, dest_root):
            continue
        target = (dest_root / member.filename).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as source, open(target, "wb") as out:
            out.write(source.read())
        extracted.append(member.filename)
    return extracted


@contextmanager
def extract_apple_health_export(zip_path: str | Path, extract_dir: str | Path) -> Iterator[Path]:
    """Extracts an Apple Health export ZIP into `extract_dir` (created if
    needed) and yields the path to export.xml. Cleans up the extracted files
    on exit regardless of success/failure. Raises AppleHealthImportError with
    a safe message for a malformed/incomplete ZIP or a missing export.xml."""

    zip_path = Path(zip_path)
    dest_root = Path(extract_dir)
    dest_root.mkdir(parents=True, exist_ok=True)

    try:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                bad_member = zf.testzip()
                if bad_member is not None:
                    raise AppleHealthImportError(
                        "The Apple Health export ZIP appears incomplete or corrupted "
                        f"(problem detected in '{bad_member}')."
                    )
                _safe_extract_all(zf, dest_root)
        except zipfile.BadZipFile as exc:
            raise AppleHealthImportError(
                "The file provided is not a valid ZIP archive, or it is corrupted."
            ) from exc

        export_xml: Path | None = None
        for candidate in _EXPORT_XML_CANDIDATES:
            path = dest_root / candidate
            if path.exists():
                export_xml = path
                break
        if export_xml is None:
            matches = list(dest_root.rglob("export.xml"))
            export_xml = matches[0] if matches else None
        if export_xml is None:
            raise AppleHealthImportError(
                "No export.xml file was found inside the provided archive — this doesn't "
                "look like an Apple Health export."
            )

        yield export_xml
    finally:
        _cleanup(dest_root)


def _cleanup(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        except OSError:
            continue
    try:
        root.rmdir()
    except OSError:
        pass
