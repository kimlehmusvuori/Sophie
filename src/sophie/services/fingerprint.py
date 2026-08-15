"""Streaming content fingerprint for import idempotence — never loads a
whole file (which may be hundreds of MB) into memory at once."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


def compute_file_fingerprint(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
