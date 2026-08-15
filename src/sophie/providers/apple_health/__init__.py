"""Apple Health import provider: safe ZIP extraction + streaming XML
parsing. See docs/PRODUCT_SPEC.md §9-11 and docs/PRIVACY.md — the raw
export.xml/ZIP is never persisted, and this package never imports
sqlalchemy/streamlit/httpx."""

from sophie.providers.apple_health.errors import AppleHealthImportError
from sophie.providers.apple_health.xml_stream_parser import parse_apple_health_export
from sophie.providers.apple_health.zip_extract import extract_apple_health_export

__all__ = ["AppleHealthImportError", "extract_apple_health_export", "parse_apple_health_export"]
