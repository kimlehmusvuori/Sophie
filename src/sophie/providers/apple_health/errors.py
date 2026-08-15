from __future__ import annotations


class AppleHealthImportError(Exception):
    """Raised for any Apple Health import failure. The message is always
    safe to show a user (no paths with sensitive content, no tracebacks)."""
