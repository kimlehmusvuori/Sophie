# Sophie — Privacy

Sophie is local-first. This document is the map of every place data leaves the local machine, and
what is retained on disk.

## Retention

| Source | Retained? |
|---|---|
| Apple Health ZIP/XML | No — streamed, parsed, deleted after processing. Never written to `data/`. |
| Sports Tracker ZIP/FIT/GPX | No — parsed, deleted after processing. |
| Clinical PDF/CSV/JSON | Source file not retained after confirmed import (unless the user explicitly configures otherwise); the *interpreted, user-confirmed* `lab_result` rows are retained in SQLite. |
| Body composition report | Same as clinical: interpreted rows retained, source file not retained by default. |
| Outlook access/refresh tokens | Stored via the OS-native credential store the local `msal` token cache abstraction targets (see `sophie.providers.calendar.token_cache`) — **never** in the SQLite application database, never logged. |
| Weight, HRV, sleep, workouts, lab values, etc. | Retained in local SQLite (`data/sophie.db`) as normalized/derived rows — this is the product's actual data store. |

## What is sent to the LLM, and what is not

Two separate LLM surfaces exist, each with its own sanitization boundary function, but the same
rule applies to both: only already-derived summary/status data ever reaches a provider.

**Coach (structured weekly plan, OpenAI only).** Sent: processed daily/weekly summaries, sanitized
calendar metadata (free/busy windows and counts only), relevant user configuration (goals,
preferences, current block), the manual check-in, current health *domain statuses* (e.g. "training
load: elevated"; never raw samples), and Sophie memory the user has explicitly approved. See
`sophie.services.sunday_review.build_coach_context()` — the single place that assembles what the
coach LLM sees.

**Chat (free-form Q&A, user picks Claude/ChatGPT/Grok).** Sent: the same category of data as the
coach — health domain statuses, trailing 30-day averages (sleep, resting HR, HRV, weight, steps —
rounded numbers with a data-quality count, never a raw per-sample series), goals, and Sophie
memory. See `sophie.services.chat_context.build_chat_context()` — the single place that assembles
what the chat LLM sees. Whichever provider you pick (Anthropic/OpenAI/xAI) receives only this
sanitized context plus your typed question and prior chat turns — never raw data, regardless of
provider. Chat answers pass through the same forbidden-language safety filter
(`sophie.domain.clinical_safety.contains_forbidden_language`) the clinical domain uses before being
shown, so a provider that ignores the system prompt's medical-safety instructions still can't
produce a diagnostic-sounding answer.

**Never sent, to either surface:** raw Apple Health export data, raw blood test values/PDFs,
complete clinical documents, raw FIT/GPX files, GPS routes/coordinates, raw calendar event
titles/bodies/attendees, access or refresh tokens. There is no code path from a raw import table
into either context-builder function.

## Calendar privacy

Sophie retains only busy/free intervals, start/end, all-day flag, and meeting density from
Outlook — never titles, bodies, attendee names/addresses. If local inspection of an event title is
ever needed for something like travel classification, it happens locally in the calendar provider
and the result (a classification, not the title) is what persists — the title itself is discarded
immediately and never sent to the LLM.

## Weather & location privacy

Weather uses an explicitly user-configured coarse location (city / approximate area / manual
lat-lon in `.env` or Memory/Config) — never inferred from historical GPX routes, and historical
routes are never uploaded to a weather provider. If weather is unavailable, planning proceeds
without it.

## Git safety

`.gitignore` excludes `.env`, token caches, the SQLite database, Apple Health/FIT/GPX/health ZIPs,
clinical and body-composition reports, and any generated personal export. Only synthetic fixtures
under `tests/fixtures/` are committed. If real personal files are later used locally for a QA
pass, they must stay outside version control (see `docs/README` real-data QA guidance).

## Verification checklist (see also PRODUCT_SPEC acceptance criteria)

- [ ] `grep -r "openai\|anthropic" src/sophie/providers/apple_health src/sophie/providers/sports_tracker src/sophie/providers/clinical` → no hits (importers never call any LLM).
- [ ] `sophie.services.sunday_review.build_coach_context()` inputs traced to only summary/derived tables.
- [ ] `sophie.services.chat_context.build_chat_context()` inputs traced to only summary/derived tables.
- [ ] `git log --all --stat` for this repo never contains a real personal data file.
- [ ] Token cache path is outside `data/sophie.db` and outside the git tree.
