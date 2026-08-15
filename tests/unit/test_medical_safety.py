"""Backstop scan for forbidden diagnostic/score-like language. Passing this
test is necessary but not sufficient — see docs/HEALTH_LOGIC_AND_SAFETY.md,
human review against that document is still required for any domain change."""

from __future__ import annotations

from pathlib import Path

from sophie.domain.clinical_safety import (
    clinician_discussion_note,
    contains_forbidden_language,
    material_change_note,
    out_of_range_note,
)

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "src" / "sophie" / "domain"

_FORBIDDEN_SOURCE_PATTERNS = (
    "sophie health score",
    "health_score =",
    "biological_age",
    "biological age",
    "injury_probability",
    "disease_probability",
    "risk_score",
)


def test_no_composite_health_score_in_domain_source():
    offenders = []
    for path in DOMAIN_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for pattern in _FORBIDDEN_SOURCE_PATTERNS:
            if pattern in text:
                offenders.append((str(path.name), pattern))
    assert offenders == [], f"forbidden score-like pattern found: {offenders}"


def test_clinical_safety_templates_are_clean():
    assert contains_forbidden_language(out_of_range_note("HbA1c")) is False
    assert contains_forbidden_language(material_change_note("ANA")) is False
    assert contains_forbidden_language(clinician_discussion_note()) is False


def test_forbidden_language_detector_catches_disease_claims():
    bad_examples = [
        "You have rheumatoid arthritis.",
        "This rules out cardiovascular disease.",
        "Your risk of developing diabetes is 40%.",
        "You should take metformin.",
    ]
    for example in bad_examples:
        assert contains_forbidden_language(example) is True, example
