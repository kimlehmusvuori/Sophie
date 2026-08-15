# Sophie — Product Specification

## What Sophie is

Sophie is a personal health, training and performance decision system. It combines Apple Health,
Apple Watch data, historical training, current training goals, body-weight/composition trends,
nutrition information, calendar reality, physical recovery context, mental wellbeing, long-term
cardiovascular/metabolic health, periodic clinical/laboratory data, and short subjective check-ins
to answer one question every week:

> What should I realistically do next week, and am I moving toward better overall health?

Sophie behaves increasingly like a personal health operating system, not just a running-plan
generator — but the core product stays deliberately simple and low-friction.

## Operating philosophy

- The primary management moment is the **Sunday Review**. Sophie is not a daily biohacking
  dashboard.
- Reduce planning friction, support sustainable health, running improvement, sustainable weight
  reduction, mental wellbeing; recognize work/family constraints; avoid unnecessary manual
  tracking; learn from actual outcomes; use passive data wherever possible.
- Fundamental training principle: **do not maximize how tired the user can become — maximize the
  physical capacity and consistency the user carries forward.**

## User profile (editable, never hard-coded into planning logic)

All values below are seeded defaults in `user_config` / `profile`, editable via Memory / Config.
Planning and health logic must read these values, not assume them.

- Male, born 1988, height ~179cm, current weight ~90kg.
- Long-term weight objective: below 80kg, gradual and sustainable.
- Experienced endurance runner; previous marathon ~3:45; current capacity materially below peak.
- Recent reference run: ~13.5km in 1:26:59.
- Current race objective: half marathon, May 2027.
- Max 3 running sessions/week. Padel every Thursday.
- Training fits around work/family — not an added stressor.
- Gluten intolerant. Prefers protein-heavy, lower-carbohydrate / paleo-inspired eating.
- Often fasts ~18:00–11:30.
- Mental energy and general wellbeing are goals alongside physical performance.

Family-history context (cardiovascular disease, diabetes, autoimmune/inflammatory disease, other)
is optional, private, local-only, structured free-text-adjacent context — **never** a diagnostic
input. It must never appear in demo fixtures or source-controlled defaults.

## Priority order (trade-off guide)

1. Reliable personal data foundation
2. Excellent Sunday Review + calendar-aware training planning
3. Memory + plan-vs-actual + Decision Log
4. High-value physical and mental health intelligence from existing data
5. Clinical/laboratory and body-composition longitudinal context
6. Supporting lifestyle functionality (lightweight nutrition suggestions)

Secondary features (5, 6) must never compromise 1–3.

## Current four-week running block (seeded, editable `plan`/`session` data)

**Week 1** — Quality: 6×250m uphill @ ~RPE 8/10 (hard, controlled, not maximal). Easy: 8–9km very
easy + optional 4×~10s hill strides. Long: 13.5–14.5km easy.

**Week 2** — Quality: 3×8min controlled threshold, 2–3min easy between. Easy: 9–10km easy. Long:
14.5–15.5km easy.

**Week 3** — Quality: 7×250m uphill. Easy: 9–11km easy. Long: 16–17km only if prior
training/recovery has gone well, otherwise ~15–16km.

**Week 4** — Quality: 3×6min controlled threshold. Easy: 7–9km easy. Long: 12–14km easy.

## Weekly training rules

- Maximum 3 running sessions/week. Priority order: long run > quality > easy run. A constrained
  week may have two sessions; a highly constrained week may have one.
- One real quality session maximum per week. Allowed quality: controlled threshold, uphill
  repetitions, easy/steady progression, short strides, ~3×5min steady.
- Avoid: hero workouts, maximal sprinting, aggressive VO2max programming, multiple hard running
  sessions in a week.
- Thursday padel is meaningful physical load. Optimize around (not hard-block): avoid hard Friday
  running, avoid a Friday long run right after hard Thursday padel, avoid quality the day after a
  long run, avoid several hard sessions on consecutive days. These are soft constraints scored by
  the feasibility engine, not inflexible laws.

## Scheduling preferences (seeded, editable)

- Drop-off 08:00–08:30; earliest normal weekday session 08:45; avoid sessions after 20:00.
- Weekday preference order: post-drop-off → lunch → after work.
- Long run Friday–Sunday, Saturday preferred, Sunday second choice.
- Preserve one day without structured training where practical. Walking is always fine. Family
  reality outranks theoretical perfection.

## Sunday Review workflow

A–H steps: Data status → Last week (plan vs actual, load, recovery, weight) → Manual check-in
(pain, stress/mental load, fasting, weekly note, and nutrition/alcohol only if Apple Health
nutrition data is weak) → Wellbeing (WHO-5 if due) → Next week (calendar load, windows, padel,
weather) → Sophie recommendation (verdict, ≤3 reasons, recommended plan, conservative alternative)
→ Modify/approve → Final confirmation (only then write to Outlook).

See `docs/DATA_DICTIONARY.md` for entity detail, `docs/HEALTH_LOGIC_AND_SAFETY.md` for the health
domain methodology and safety boundary, and `docs/ARCHITECTURE.md` for how these pieces fit
together in code.

## Acceptance path (condensed)

The product must let the user: launch locally → use Demo Mode → import Apple Health → import
Sports Tracker → see baseline, training load, recovery, cardio trend, sleep/circadian/daylight,
everyday movement, wellbeing trend, hearing/noise context → import lab results → import body
composition → run a full Sunday Review (plan-vs-actual → check-in → next week → verdict → plan →
conservative alternative → modify → approve → confirm → write to Outlook → save decision) → return
the following Sunday and compare plan to actual → review Decision Log → edit Memory/Config →
export processed Sophie data.

Full acceptance criteria are in the original build prompt (§78–80); this file is the durable
summary kept in sync with what is actually built.
