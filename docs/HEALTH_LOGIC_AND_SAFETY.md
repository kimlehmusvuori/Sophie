# Sophie — Health Logic & Safety

Read this before modifying anything under `sophie.domain` or `sophie.services` that interprets
health data, or any UI text that describes a health status.

## The hard boundary

Sophie is **not a diagnostic medical device**. It must never:

- claim to detect, diagnose, or rule out any disease (including autoimmune disease, cardiovascular
  disease, diabetes, Sjögren's, rheumatoid arthritis);
- produce a disease-probability percentage;
- produce an invented "biological age";
- produce an injury probability;
- produce an exact recovery percentage;
- produce an opaque composite risk score;
- prescribe treatment or medication;
- invent a laboratory reference range (only the supplying lab's own range is ever shown);
- recommend broad medical screening without clinician context.

Sophie's actual role: longitudinal tracking, trend detection, personal-baseline deviation context,
surfacing explicit laboratory abnormalities *as supplied by the lab*, and — only when there is a
genuinely notable pattern — a single, consistent phrase:

> "Consider discussing this pattern with your healthcare professional."

Never a stronger claim than that. Never a diagnostic claim.

## No composite health score

Do not create `Sophie Health Score = 83/100` or any single-number rollup across domains. Health
domains (training capacity, cardiovascular/metabolic trajectory, recovery, circadian/sleep, mental
wellbeing, everyday movement, hearing/noise, clinical/laboratory, body composition) are always
shown separately, each with its own status/trend + supporting evidence + data quality.

## Status vocabulary (use these, not invented ones)

- Training load: **Low / Typical / Elevated / Very elevated**
- Recovery deviation: **Normal / Watch / Concern**
- Cardio/metabolic trajectory: **Improving / Stable / Watch / Insufficient data**
- Everything else: plain trend language ("increasing", "declining", "no change") plus explicit
  **data quality** (`sufficient` / `limited` / `insufficient`) — never silently omitted.

## Personal baseline, not population norms

Recovery deviation and everyday-movement baselines compare the user to **their own** historical
distribution (e.g. trailing 60–90 day median/IQR), not a generic population cutoff. Where a
domain genuinely needs an external reference (e.g. a laboratory's own reference interval, or the
official WHO-5 scoring table), that source must be explicitly named and versioned in code and in
this document (see below).

### Versioned external references in use

- **WHO-5 Well-Being Index** — official 5-item questionnaire, standard 0–5 Likert scoring per
  item, raw score ×4 = percentage score (0–100). Source: WHO Regional Office for Europe, 1998
  version (Psychiatric Research Unit, Frederiksborg). Implemented in
  `sophie.domain.wellbeing.WHO5_QUESTIONS` / `score_who5()`. Do not alter wording or scoring
  without updating `instrument_version` and this section.
- Laboratory reference intervals: always the value supplied by the importing lab on `lab_result`
  (`reference_low`/`reference_high`/`reference_text`). Sophie never substitutes a different
  interval.

## Training load methodology (transparent, not a black box)

`sophie.domain.training_load` computes a relative-load ratio: recent (7-day, session-type-weighted
duration × effort proxy) load versus the user's own trailing 28-day baseline. Effort proxy uses,
in order of availability: heart-rate-based relative intensity → RPE/session-type default weights
when no HR data exists. The ratio maps to Low/Typical/Elevated/Very elevated using fixed,
documented band edges in that module (not tuned per user, not marketed as clinically validated).
This is a load-awareness heuristic for weekly planning, not an injury-risk model — the UI must
never phrase it as one.

## Recovery deviation methodology

`sophie.domain.recovery` flags a day as **Watch** or **Concern** only when ≥2 independent signals
(resting HR, HRV, sleep duration/efficiency, respiratory rate, wrist-temperature deviation) are
simultaneously outside the user's own recent range, weighted by how many signals are actually
available (`data_quality`). A single deviated signal, or too few available signals, never escalates
past **Normal** with a data-quality note. This is weekly planning context — it must not become a
daily readiness push notification or gating mechanism outside Sunday Review.

## Aerobic efficiency proxy

`sophie.domain.aerobic_efficiency` compares pace-to-heart-rate ratio across *reasonably similar*
easy/steady runs (session-type + duration band matched) over a multi-week trailing window. This is
explicitly called an "aerobic efficiency proxy" in all UI copy — never "running economy" (a
laboratory metabolic-testing term Sophie cannot measure).

## Autoimmune / clinical pattern language

Allowed: "This measurement is outside the supplied laboratory reference interval." / "This marker
has changed materially across several measurements." / "Given this combination of longitudinal
data and what you've entered, consider discussing the pattern with your healthcare professional."

Disallowed: any sentence that names a specific disease as present, likely, or ruled out. A
positive antibody value (ANA, anti-SSA/Ro, anti-CCP, etc.) is tracked as a longitudinal
measurement only — it is never turned into a disease inference, and no rule may fire that says
"positive antibody => condition".

## Family history

`family_history_item` rows are context-only inputs a future clinical-pattern prompt *may* mention
alongside lab trends (e.g. "family history of autoimmune disease noted" as one contextual fact
among several) — they must never themselves trigger a disease claim, and must never appear in
demo/synthetic fixtures (see `docs/PRIVACY.md`).

## Reviewing changes against this document

Any change to a domain module under `sophie/domain/{training_load,recovery,cardio,
aerobic_efficiency,circadian,wellbeing,hearing,clinical}.py`, or to UI copy that surfaces their
output, should be checked against this file before merging. `tests/unit/test_medical_safety.py`
greps for a small set of forbidden phrases/patterns as a backstop — passing that test is necessary
but not sufficient; human judgement against this document is still required.
