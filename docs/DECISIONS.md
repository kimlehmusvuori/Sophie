# Sophie — Engineering Decisions Log

Durable record of material decisions made during the build, and why. Add to this file rather than
re-litigating a settled decision.

## 2026-08 — Initial build

- **Stack**: Python 3.12 / Streamlit / SQLite / SQLAlchemy 2.x / Alembic / Pydantic v2 /
  pydantic-settings / lxml / fitparse / MSAL / HTTPX / OpenAI SDK / pytest / Ruff / mypy, per the
  build brief. No deviation.
- **FIT parser**: chose `fitparse` (pure-Python, maintained, no native build step) over
  `garmin_fit_sdk` for simplicity of local install; revisit only if a real Sports Tracker FIT file
  exposes a field `fitparse` can't read.
- **Layering**: strict `ui -> services -> domain -> repositories/providers`, enforced by a
  boundary test that greps for `streamlit` imports outside `sophie/ui/streamlit/`. This is the
  single most important structural decision protecting future frontend portability.
- **profile_id everywhere, no auth**: every user-owned table carries `profile_id` (UUID) with
  exactly one seeded `Profile` row, to avoid a future multi-user schema rewrite, without building
  any actual authentication (explicitly out of scope).
- **No composite health score, ever**: enforced both by code review discipline and by
  `tests/unit/test_medical_safety.py` scanning for score-like patterns in domain output.
- **Calendar**: real MSAL/Graph delegated-auth implementation is built and unit/mock-tested; a
  local ICS/mock fallback provider satisfies the "must work without live credentials" requirement.
  No live Graph call has been made from this environment (no user credentials available here) —
  see the final handoff report for exactly what "implemented" vs "live-tested" means.
- **LLM**: OpenAI is the default coach provider behind a provider interface; a deterministic
  rules-only fallback is the default when no API key is configured, so the product is fully
  usable without any LLM access.
- **Clinical PDF import**: local extraction only, always requires explicit user confirmation of
  parsed values before any `lab_result` row is written; no OCR by default.
- **Demo Mode**: synthetic fixtures only, built to be structurally representative without
  resembling the user's real (unentered) family-health history.

## 2026-08 — Build completion

- Fixed a real correctness bug found during end-to-end verification:
  `plan_vs_actual.py` originally compared a planned session's intent
  (`long`/`quality`/`easy`) directly against a real workout's recorded
  `activity_type` (`run`/`padel`/...) — these are different vocabularies, so
  a completed run could never match its plan. Added an explicit
  intent-to-activity-type mapping and fixed the demo-data generator and its
  tests to use the corrected model.
- Added `weekly_summary_service.compute_and_store_weekly_summary()` — the
  `weekly_summary` table was defined in the schema but nothing computed it
  from plan/session/workout data; Sunday Review's "last week" comparison
  now derives it live instead of reading an always-empty row.
- Verified end to end with a live headless Streamlit session driven by
  Playwright (not just imports/unit tests): Demo Mode seeding, all 4 nav
  pages, the full Sunday Review flow (data status → check-in → WHO-5 →
  calendar/weather → recommendation → approve → decision save), zero
  tracebacks. This is what "Ready" in the final handoff is based on.
- Final privacy/medical-safety grep sweep (composite-score patterns,
  forbidden diagnostic language, explicit-exclusion features, hardcoded
  secrets, tracked personal-data files) came back clean — see the final
  handoff report for the full checklist.

Add further entries below as the product evolves.
