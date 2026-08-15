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

Add further entries below as the build progresses.
