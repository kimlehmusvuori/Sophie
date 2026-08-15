"""Cardio-metabolic / heart-health trajectory. NEVER computes a proprietary
cardiovascular-risk number and NEVER diagnoses disease — it reports simple
per-metric trend direction plus an overall qualitative rollup, always with
supporting evidence. See docs/HEALTH_LOGIC_AND_SAFETY.md."""

from __future__ import annotations

from dataclasses import dataclass, field


def _trend_from_series(values: list[float], higher_is_better: bool) -> str:
    if len(values) < 4:
        return "insufficient_data"
    half = len(values) // 2
    earlier = sum(values[:half]) / half
    later = sum(values[half:]) / (len(values) - half)
    diff_pct = (later - earlier) / earlier if earlier else 0.0
    if not higher_is_better:
        diff_pct = -diff_pct
    if diff_pct >= 0.03:
        return "improving"
    if diff_pct <= -0.03:
        return "watch"
    return "stable"


@dataclass
class CardioInputs:
    vo2_max_series: list[float] = field(default_factory=list)  # chronological
    resting_hr_series: list[float] = field(default_factory=list)
    weight_series: list[float] = field(default_factory=list)
    weight_goal_kg: float | None = None
    lab_abnormal_flags: list[str] = field(default_factory=list)  # e.g. ["LDL cholesterol"]


@dataclass
class CardioResult:
    overall_trend: str  # improving/stable/watch/insufficient_data
    vo2_max_trend: str
    resting_hr_trend: str
    weight_trend: str
    evidence: dict
    data_quality: str


def compute_cardio_trend(inputs: CardioInputs) -> CardioResult:
    vo2_trend = _trend_from_series(inputs.vo2_max_series, higher_is_better=True)
    rhr_trend = _trend_from_series(inputs.resting_hr_series, higher_is_better=False)

    weight_trend = "insufficient_data"
    if len(inputs.weight_series) >= 4:
        if inputs.weight_goal_kg is not None and inputs.weight_series[-1] > inputs.weight_goal_kg:
            weight_trend = _trend_from_series(inputs.weight_series, higher_is_better=False)
        else:
            weight_trend = "stable"

    trends = [t for t in (vo2_trend, rhr_trend, weight_trend) if t != "insufficient_data"]

    if not trends:
        overall = "insufficient_data"
    elif "watch" in trends or inputs.lab_abnormal_flags:
        overall = "watch" if "watch" in trends else "stable"
    elif all(t == "improving" for t in trends):
        overall = "improving"
    else:
        overall = "stable"

    data_quality = "sufficient" if len(trends) >= 2 else ("limited" if trends else "insufficient")

    evidence = {
        "vo2_max_points": len(inputs.vo2_max_series),
        "resting_hr_points": len(inputs.resting_hr_series),
        "weight_points": len(inputs.weight_series),
        "lab_abnormal_flags": inputs.lab_abnormal_flags,
    }

    return CardioResult(
        overall_trend=overall,
        vo2_max_trend=vo2_trend,
        resting_hr_trend=rhr_trend,
        weight_trend=weight_trend,
        evidence=evidence,
        data_quality=data_quality,
    )
