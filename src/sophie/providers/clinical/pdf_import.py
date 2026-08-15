"""PDF import for provider-independent clinical lab results.

PDF text/table extraction quality is inherently uncertain, so this module:

- ALWAYS returns requires_confirmation=True for anything it extracts.
- Tries table extraction first (page.extract_tables()), and only falls back
  to a conservative line-based text heuristic when a page has no tables.
- Never uses OCR. If a page's extract_text() is empty, that page is treated
  as a (possibly scanned) image with no usable text layer. If the whole
  document has no extractable text anywhere, zero results are returned with
  an explicit warning telling the user to get structured data or enter
  values manually — see docs/HEALTH_LOGIC_AND_SAFETY.md and the product
  spec's PDF-handling requirement.
- Only emits a ParsedLabResult when test_name + value are reasonably
  unambiguous; anything else is skipped with a warning describing what
  could not be parsed, never guessed at.
- Never produces any diagnostic interpretation — this module only extracts
  test_name/value/unit/reference/flag data.

This module must never import sqlalchemy/streamlit or call an LLM/network
API — it returns plain dataclasses; a service layer persists them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

from sophie.domain.clinical_reference import canonicalize_test_name
from sophie.domain.import_types import ClinicalImportOutcome, ParsedLabResult

from ._common import (
    first_present,
    normalize_key,
    parse_date,
    parse_float,
    parse_reference_range_text,
    parse_value,
)

SCANNED_IMAGE_WARNING = (
    "This PDF appears to be a scanned image with no extractable text — please obtain "
    "structured/tabular data or enter measurements manually."
)

_DOC_DATE_PATTERNS = (
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b"),
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b"),
)

# Conservative line heuristic: NAME (2+ spaces) VALUE (optional unit)
# (optional "(LOW - HIGH)" reference range). Anything not matching this
# shape is left alone rather than guessed at.
_TEXT_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-/() ]{1,60}?)\s{2,}"
    r"(?P<value>[<>]?-?\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>[A-Za-zµ%/^0-9]+)?\s*"
    r"(?:\(?\s*(?P<low>-?\d+(?:[.,]\d+)?)\s*[-–]\s*(?P<high>-?\d+(?:[.,]\d+)?)\s*\)?)?\s*$",
)


def _find_document_date(page_texts: list[str]) -> Any:
    joined = "\n".join(t for t in page_texts if t)
    for pattern in _DOC_DATE_PATTERNS:
        match = pattern.search(joined)
        if match:
            parsed = parse_date(match.group(1))
            if parsed is not None:
                return parsed
    return None


def _table_row_dict(headers: list[str], row: list[str | None]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i, header in enumerate(headers):
        if i >= len(row) or row[i] is None:
            continue
        out[header] = str(row[i]).strip()
    return out


def _from_table_row(
    row_dict: dict[str, str],
    doc_date: Any,
    page_no: int,
    warnings: list[str],
) -> ParsedLabResult | None:
    test_name_raw = first_present(row_dict, "test_name")
    value_raw = first_present(row_dict, "value")

    if test_name_raw is None or not str(test_name_raw).strip():
        return None  # blank/separator/header-ish row — not worth a warning
    test_name = str(test_name_raw).strip()

    if value_raw is None:
        warnings.append(f"Page {page_no}: row for {test_name!r} has no parseable value, skipped.")
        return None

    value, value_text = parse_value(value_raw)
    if value is None and value_text is None:
        warnings.append(f"Page {page_no}: row for {test_name!r} has no parseable value, skipped.")
        return None

    date_raw = first_present(row_dict, "sample_date")
    row_date = parse_date(date_raw) if date_raw is not None else None
    sample_date = row_date or doc_date
    if sample_date is None:
        warnings.append(
            f"Page {page_no}: could not determine a sample date for {test_name!r}, skipped.",
        )
        return None

    canonical_id, category = canonicalize_test_name(test_name)

    unit_raw = first_present(row_dict, "unit")
    unit = str(unit_raw).strip() if unit_raw is not None else None

    reference_low = parse_float(first_present(row_dict, "reference_low"))
    reference_high = parse_float(first_present(row_dict, "reference_high"))
    reference_range_raw = first_present(row_dict, "reference_range")
    reference_text = str(reference_range_raw).strip() if reference_range_raw is not None else None
    if reference_low is None and reference_high is None and reference_text:
        reference_low, reference_high = parse_reference_range_text(reference_text)

    flag_raw = first_present(row_dict, "abnormal_flag")
    abnormal_flag = str(flag_raw).strip() if flag_raw is not None else None

    return ParsedLabResult(
        sample_date=sample_date,
        test_name=test_name,
        canonical_test_id=canonical_id,
        value=value,
        value_text=value_text,
        unit=unit,
        reference_low=reference_low,
        reference_high=reference_high,
        reference_text=reference_text,
        abnormal_flag=abnormal_flag,
        category=category,
        notes=None,
    )


def _parse_table(
    table: list[list[str | None]],
    doc_date: Any,
    page_no: int,
    warnings: list[str],
) -> list[ParsedLabResult]:
    if not table or len(table) < 2:
        return []
    headers = [normalize_key(cell or "") for cell in table[0]]
    results: list[ParsedLabResult] = []
    for row in table[1:]:
        if row is None or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        row_dict = _table_row_dict(headers, row)
        result = _from_table_row(row_dict, doc_date, page_no, warnings)
        if result is not None:
            results.append(result)
    return results


def _parse_text_line(
    line: str,
    doc_date: Any,
    page_no: int,
    warnings: list[str],
) -> ParsedLabResult | None:
    stripped = line.strip()
    if not stripped:
        return None
    match = _TEXT_LINE_RE.match(stripped)
    if not match:
        if _looks_like_data_line(stripped):
            warnings.append(f"Page {page_no}: could not confidently parse line: {stripped!r}")
        return None

    if doc_date is None:
        warnings.append(
            f"Page {page_no}: no document date found; skipped otherwise-parseable "
            f"line: {stripped!r}",
        )
        return None

    test_name = match.group("name").strip()
    if not test_name:
        return None
    value, value_text = parse_value(match.group("value"))
    canonical_id, category = canonicalize_test_name(test_name)

    unit = match.group("unit")
    unit = unit.strip() if unit else None

    low_raw, high_raw = match.group("low"), match.group("high")
    reference_low = parse_float(low_raw) if low_raw else None
    reference_high = parse_float(high_raw) if high_raw else None
    reference_text = f"{low_raw}-{high_raw}" if low_raw and high_raw else None

    return ParsedLabResult(
        sample_date=doc_date,
        test_name=test_name,
        canonical_test_id=canonical_id,
        value=value,
        value_text=value_text,
        unit=unit,
        reference_low=reference_low,
        reference_high=reference_high,
        reference_text=reference_text,
        abnormal_flag=None,
        category=category,
        notes=None,
    )


def _looks_like_data_line(line: str) -> bool:
    """A very rough filter so we don't emit a warning for every line of
    boilerplate/header text on the page — only lines that look like they
    were trying to report a measurement (contain a digit) get flagged as
    unparseable."""

    return any(ch.isdigit() for ch in line) and len(line.strip()) > 3


def import_lab_results_pdf(path: str | Path) -> ClinicalImportOutcome:
    """Imports lab results from a PDF via pdfplumber. Always requires
    confirmation — PDF extraction is inherently uncertain. Never uses OCR."""

    file_path = Path(path)
    results: list[ParsedLabResult] = []
    warnings: list[str] = []
    page_texts: list[str] = []
    any_text_found = False

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                page_texts.append(text)

        doc_date = _find_document_date(page_texts)

        for page_no, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            if tables:
                any_text_found = True
                for table in tables:
                    results.extend(_parse_table(table, doc_date, page_no, warnings))
                continue

            text = page.extract_text()
            if not text:
                continue
            any_text_found = True
            for line in text.splitlines():
                parsed = _parse_text_line(line, doc_date, page_no, warnings)
                if parsed is not None:
                    results.append(parsed)

    if not any_text_found:
        warnings.append(SCANNED_IMAGE_WARNING)

    return ClinicalImportOutcome(results=results, requires_confirmation=True, warnings=warnings)
