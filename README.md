# Sophie

Sophie is a personal, local-first health, training and performance decision system. It combines
Apple Health, historical training, body-weight trends, calendar reality, recovery context, mental
wellbeing, and periodic clinical data to answer one question every week:

> **What should I realistically do next week, and am I moving toward better overall health?**

Everything runs on your own computer. Your data stays in a local file (`data/sophie.db`) unless
you explicitly export it or connect Outlook/weather/an AI provider.

## 1. Install

Requirements: **Python 3.12** (check with `python3 --version`; on macOS install via
[python.org](https://www.python.org/downloads/) or `brew install python@3.12`).

```bash
cd sophie
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Copy the example environment file and edit it later as needed (see sections below):

```bash
cp .env.example .env
```

## 2. Start Sophie

```bash
source .venv/bin/activate
streamlit run src/sophie/ui/streamlit/app.py
```

Your browser opens automatically at `http://localhost:8501`. The database and its migrations are
created automatically on first run, in `./data/sophie.db`.

To stop Sophie, press `Ctrl+C` in the terminal.

## 3. Demo Mode

Demo Mode is **on by default** (`SOPHIE_DEMO_MODE=true` in `.env`). On first launch, click
**"(Re)generate demo data"** in the sidebar to populate 8 weeks of realistic synthetic training,
health, wellbeing, lab, and body-composition data — enough to try every screen, including a full
Sunday Review, without needing any of your own files yet.

Demo data is entirely synthetic and is regenerated (replacing itself) each time you click the
button — it never contains anything resembling real personal or family health history.

When you're ready to use your own data, set `SOPHIE_DEMO_MODE=false` in `.env` and restart Sophie.

## 4. Import your Apple Health data

1. On your iPhone: **Health app → your profile picture (top right) → Export All Health Data**.
   This produces a ZIP file (can be several hundred MB — that's normal).
2. AirDrop, email, or cable-transfer that ZIP to the computer running Sophie.
3. In Sophie's Memory/Config page (or a future dedicated import screen), point Sophie at the ZIP
   file path.

Sophie streams the file, extracts normalized workouts and daily health summaries, and **discards
the ZIP/XML afterward** — the original file is never copied into Sophie's data folder. A metric
catalogue (under Memory/Config → "Apple Health data status") shows every record type Apple Health
exported and whether Sophie currently uses it.

Re-importing the same export again is safe — Sophie recognizes identical content and skips it
rather than duplicating data.

## 5. Import Sports Tracker data

Point Sophie at your historical Sports Tracker export (a ZIP containing `.fit`/`.gpx` files, or an
already-unzipped folder of them). Sophie deduplicates a workout that appears in both FIT and GPX
form, and — separately — deduplicates against any matching Apple Health workout for the same
real-world activity.

## 6. Connect Outlook (optional)

Outlook lets Sophie see next week's free/busy time and write approved training sessions onto your
calendar. This is **entirely optional** — Sophie works fully with a manually uploaded `.ics` file
or with no calendar at all.

Full setup (Entra ID app registration, permissions, first sign-in) is in
**[docs/OUTLOOK_SETUP.md](docs/OUTLOOK_SETUP.md)**. Short version:

1. Register a free app at [entra.microsoft.com](https://entra.microsoft.com) (5 minutes, see the
   doc for exact steps).
2. Put the resulting client ID into `.env` as `MS_GRAPH_CLIENT_ID`.
3. Restart Sophie and click **Connect Outlook**.

Sophie only ever reads free/busy times (never meeting titles or attendees) and only ever writes
back events it created itself.

## 7. Connect an AI provider (optional)

Sophie's weekly coach works fully without any AI provider — it falls back to a transparent,
deterministic planner. To let it use OpenAI for extra synthesis/explanation (still subject to the
same deterministic safety rules), set in `.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Only processed summaries and sanitized context are ever sent — never raw health data, raw
calendar content, or clinical files. See [docs/PRIVACY.md](docs/PRIVACY.md).

### Chat page

The **Chat** page is a separate, free-form Q&A surface — ask about your training, sleep, recovery,
or other trends. Pick whichever provider you have a key for (Claude/Anthropic is the default):

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5
OPENAI_API_KEY=sk-...       # same key as above, reused for Chat too
XAI_API_KEY=xai-...
XAI_MODEL=grok-4
```

Same privacy rule as the coach: only sanitized summaries reach whichever provider you pick, never
raw data. Leave a key blank to leave that provider unavailable — Sophie shows this in the Chat
page's provider picker rather than crashing.

### Trends page

No setup needed — the **Trends** page shows one simple chart and trailing average per area
(training distance, sleep, weight, resting heart rate, HRV) once you've imported some data.
Toggle between Week/Month/Year to change both the chart's granularity and the average shown.

## 8. Weather (optional)

Set a coarse location in Memory/Config (or `.env`: `WEATHER_LAT`, `WEATHER_LON`,
`WEATHER_LOCATION_NAME`) to let Sophie factor next week's forecast into scheduling. This uses the
free [Open-Meteo](https://open-meteo.com) API and needs no API key. If unset or unreachable,
planning proceeds normally without it.

## 9. Import lab results and body composition (optional)

In Memory/Config, point Sophie at:

- **Lab results**: a CSV or JSON file with your test results (any reasonably named columns work —
  date/test/value/unit/reference range). A PDF lab report also works, but Sophie **always asks you
  to confirm** what it extracted before saving anything, since PDF extraction can be uncertain —
  it never trusts a PDF-derived value silently. Scanned (image-only) PDFs aren't supported; use a
  structured export or enter values manually.
- **Body composition**: a CSV/JSON export from a DEXA/InBody/similar assessment.

Sophie never invents a reference range, never infers an "abnormal" flag beyond what the lab itself
supplied, and never diagnoses anything — see
[docs/HEALTH_LOGIC_AND_SAFETY.md](docs/HEALTH_LOGIC_AND_SAFETY.md).

## 10. Backup

Your entire Sophie dataset is one file: `data/sophie.db`. To back it up, just copy that file
somewhere safe (external drive, encrypted cloud folder) while Sophie isn't running. To restore,
put the backed-up file back at `data/sophie.db` before starting Sophie again.

You can also export a full JSON/CSV snapshot of everything Sophie has derived from Memory/Config →
"Export processed data" — useful as a portable backup or for your own analysis.

## 11. Privacy

Full detail in [docs/PRIVACY.md](docs/PRIVACY.md). Summary:

- Raw Apple Health/Sports Tracker files and raw clinical documents are **never** retained after
  processing.
- Raw health data, raw calendar content, and raw clinical files are **never** sent to any AI
  provider — only processed summaries.
- Calendar access is limited to free/busy times; event titles/attendees are never stored or sent
  anywhere.
- Microsoft/Outlook tokens are stored in a local token cache file, never inside the database and
  never logged.
- `.gitignore` excludes your personal database, tokens, and any raw health/clinical files from
  version control — never commit real personal data to a shared repository.

## 12. Troubleshooting

- **"Database not configured" or startup error** — delete `data/sophie.db` only if you're certain
  you don't need its contents (this is destructive); otherwise check the terminal output for the
  actual error before doing anything drastic.
- **Apple Health import fails** — make sure you exported "All Health Data" (not a summary PDF) and
  that the ZIP wasn't corrupted in transfer; Sophie reports a clear message rather than a raw
  crash for a bad/incomplete ZIP.
- **"Outlook not connected"** — expected until you complete the steps in
  [docs/OUTLOOK_SETUP.md](docs/OUTLOOK_SETUP.md); Sunday Review works fine without it (upload an
  `.ics` file instead, or skip calendar entirely).
- **No recommendation appears / deterministic-only note** — this means no OpenAI key is configured
  or the call failed; this is by design, not a bug — the deterministic planner always has final
  say and the product remains fully usable either way.
- **Something looks wrong in the data** — check Memory/Config → "Apple Health data status" for
  import warnings, and the terminal Sophie is running in for any error detail (errors are never
  shown to you as raw Python tracebacks in the app itself).

## For developers

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md),
[CLAUDE.md](CLAUDE.md), and the rest of `docs/`. Run the test suite with:

```bash
ruff check . && ruff format --check . && mypy src && pytest --cov=src/sophie
```

Run the standalone smoke test (no Streamlit, no network) with:

```bash
python scripts/smoke_test.py
```
