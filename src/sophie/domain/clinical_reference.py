"""Canonical test-name -> (canonical_test_id, category) mapping used when
normalizing imported lab results. Deliberately small and provider-agnostic —
extend as real data reveals more test names. Matching is case-insensitive
and tries common synonyms; an unmatched test name is stored with
canonical_test_id=None and category="other" rather than guessed at.

Categories mirror docs/DATA_DICTIONARY.md §Clinical categories.
"""

from __future__ import annotations

# key: lowercased synonym -> (canonical_test_id, category)
_CANONICAL_MAP: dict[str, tuple[str, str]] = {
    # Blood count
    "hemoglobin": ("hemoglobin", "blood_count"),
    "hgb": ("hemoglobin", "blood_count"),
    "hematocrit": ("hematocrit", "blood_count"),
    "white blood cell count": ("wbc", "blood_count"),
    "wbc": ("wbc", "blood_count"),
    "platelet count": ("platelets", "blood_count"),
    "platelets": ("platelets", "blood_count"),
    # Iron / ferritin
    "ferritin": ("ferritin", "iron"),
    "iron": ("serum_iron", "iron"),
    "transferrin saturation": ("transferrin_saturation", "iron"),
    # Glucose / HbA1c
    "glucose": ("glucose_fasting", "glucose"),
    "fasting glucose": ("glucose_fasting", "glucose"),
    "hba1c": ("hba1c", "glucose"),
    "hemoglobin a1c": ("hba1c", "glucose"),
    # Lipids
    "total cholesterol": ("total_cholesterol", "lipids"),
    "ldl": ("ldl_cholesterol", "lipids"),
    "ldl cholesterol": ("ldl_cholesterol", "lipids"),
    "hdl": ("hdl_cholesterol", "lipids"),
    "hdl cholesterol": ("hdl_cholesterol", "lipids"),
    "triglycerides": ("triglycerides", "lipids"),
    # Liver
    "alt": ("alt", "liver"),
    "alanine aminotransferase": ("alt", "liver"),
    "ast": ("ast", "liver"),
    "aspartate aminotransferase": ("ast", "liver"),
    "ggt": ("ggt", "liver"),
    # Kidney
    "creatinine": ("creatinine", "kidney"),
    "egfr": ("egfr", "kidney"),
    # Thyroid
    "tsh": ("tsh", "thyroid"),
    "thyroid stimulating hormone": ("tsh", "thyroid"),
    "free t4": ("free_t4", "thyroid"),
    "free t3": ("free_t3", "thyroid"),
    # Inflammatory markers
    "crp": ("crp", "inflammatory"),
    "c-reactive protein": ("crp", "inflammatory"),
    "esr": ("esr", "inflammatory"),
    "sedimentation rate": ("esr", "inflammatory"),
    # Vitamins
    "vitamin d": ("vitamin_d", "vitamins"),
    "25-oh vitamin d": ("vitamin_d", "vitamins"),
    "vitamin b12": ("vitamin_b12", "vitamins"),
    "folate": ("folate", "vitamins"),
    # Autoimmune (tracked as longitudinal measurements only — see
    # docs/HEALTH_LOGIC_AND_SAFETY.md; never used to infer a diagnosis)
    "ana": ("ana", "autoimmune"),
    "antinuclear antibody": ("ana", "autoimmune"),
    "anti-ssa": ("anti_ssa", "autoimmune"),
    "anti-ro": ("anti_ssa", "autoimmune"),
    "anti-ssb": ("anti_ssb", "autoimmune"),
    "anti-la": ("anti_ssb", "autoimmune"),
    "rheumatoid factor": ("rheumatoid_factor", "autoimmune"),
    "rf": ("rheumatoid_factor", "autoimmune"),
    "anti-ccp": ("anti_ccp", "autoimmune"),
}

VALID_CATEGORIES = (
    "blood_count",
    "iron",
    "glucose",
    "lipids",
    "liver",
    "kidney",
    "thyroid",
    "inflammatory",
    "vitamins",
    "autoimmune",
    "other",
)


def canonicalize_test_name(test_name: str) -> tuple[str | None, str]:
    """Returns (canonical_test_id_or_None, category). Never invents a
    canonical id for an unrecognized test name — 'other' is always safe."""

    key = test_name.strip().lower()
    if key in _CANONICAL_MAP:
        canonical_id, category = _CANONICAL_MAP[key]
        return canonical_id, category
    return None, "other"
