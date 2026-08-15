# CLAUDE.md — Sophie project rules

Sophie is a local-first personal health, training and performance decision system.
Read this file before making material changes.

## Before you change things

- Read `docs/PRODUCT_SPEC.md` before any material feature change.
- Read `docs/HEALTH_LOGIC_AND_SAFETY.md` before touching anything that interprets health data.
- Read `docs/PRIVACY.md` before changing what data leaves the local machine (LLM calls, weather, calendar).

## Architecture rules

- Layering is `ui -> services -> domain -> repositories/providers`. UI (Streamlit) code must not
  contain business logic — it calls services and renders results.
- No core business logic (domain, services, repositories, providers) may import `streamlit`.
  The UI must be replaceable without touching the rest of the codebase.
- Deterministic constraints always outrank LLM recommendations. The LLM proposes; a deterministic
  validator in `services/coach_validation.py` (or equivalent) approves, repairs, or rejects.
- Raw Apple Health data, raw FIT/GPX, raw calendar titles/bodies/attendees, and raw clinical
  files/PDFs must never be sent to an LLM. Only processed summaries and sanitized metadata.
- Never diagnose or rule out disease (including autoimmune or cardiovascular disease). Sophie
  surfaces trends, deviations from personal baseline, and explicit lab-supplied abnormal flags —
  never a diagnosis, a fake risk score, or a fabricated reference range.
- Never introduce a composite "Sophie Health Score". Health domains stay separate and legible.
- Do not reintroduce previously removed exclusions (see `docs/ROADMAP.md` §Explicit exclusions)
  without the user explicitly asking for that scope back.

## Data safety rules

- Never silently overwrite or delete personal health data. Imports are additive/idempotent via
  `import_manifest`; destructive operations require explicit user action and confirmation.
- Never use destructive Git commands (`reset --hard`, `push --force`, `clean -f`, branch deletion)
  against work you didn't just create in this session, without explicit user instruction.
- Personal databases, raw health exports, tokens, and clinical files are `.gitignore`d. Never
  commit real personal data — use synthetic fixtures under `tests/fixtures/`.

## Before declaring anything complete

Run the quality gates and report actual results (don't claim success you didn't observe):

```
ruff check .
ruff format --check .
mypy src
pytest --cov=src/sophie --cov-report=term-missing
```

Also re-run a clean Alembic migration and the smoke test (`scripts/smoke_test.py`) before signing
off on any change to `src/sophie/db/`.
