# Sophie — Outlook (Microsoft Graph) Setup

Sophie's calendar integration is real delegated Microsoft Graph access via MSAL — not a stub —
but it needs an app registration and a one-time device/interactive login that only the account
owner can perform. This document is the exact activation path.

## 1. Register an app in Microsoft Entra ID (Azure AD)

1. Go to https://entra.microsoft.com → **App registrations** → **New registration**.
2. Name: `Sophie (local)`. Supported account types: your choice (personal use → "Accounts in any
   organizational directory and personal Microsoft accounts", or your own tenant only).
3. Redirect URI: platform **Mobile and desktop applications**, URI
   `http://localhost:8765/callback` (matches `MS_GRAPH_REDIRECT_URI` in `.env`).
4. After creation, note the **Application (client) ID** — this is `MS_GRAPH_CLIENT_ID`.
5. Under **API permissions**, add delegated Microsoft Graph permissions:
   `Calendars.ReadWrite`, `User.Read`. Grant admin consent if required by your tenant (not
   required for a personal Microsoft account).
6. No client secret is needed — Sophie uses a public client (desktop) flow via `msal`.

## 2. Configure Sophie

In `.env` (copied from `.env.example`):

```
MS_GRAPH_CLIENT_ID=<the Application (client) ID>
MS_GRAPH_TENANT_ID=common
MS_GRAPH_REDIRECT_URI=http://localhost:8765/callback
```

## 3. First-time sign-in

From the Streamlit app's Memory/Config → Data sources → Outlook section, click **Connect
Outlook**. Sophie opens your default browser to the Microsoft sign-in page (MSAL interactive
flow), you sign in and consent, and the browser redirects back to the local loopback listener.
The resulting token is cached via `sophie.providers.calendar.token_cache` in the OS-appropriate
local secure location — **never** inside `data/sophie.db`, never committed to git, never logged.

## 4. Without credentials configured

If `MS_GRAPH_CLIENT_ID` is unset, or sign-in hasn't happened yet, Sophie's calendar provider
reports a clear **"Outlook not connected"** status in Sunday Review's data-status step and falls
back to a manual/ICS-based availability input so planning can still proceed — it does not crash
or silently pretend a connection exists.

## 5. What Sophie reads and writes

- **Reads**: free/busy intervals for the target week only (start/end/all-day). Event
  titles/bodies/attendees are never persisted or sent to the LLM (see `docs/PRIVACY.md`).
- **Writes**: only events Sophie itself created for approved training sessions, tagged with a
  Sophie-owned marker (category/extended property) so future syncs can identify and update/delete
  *only* Sophie's own events — unrelated events are never touched.

## 6. Verifying without live credentials (this build environment)

This development environment has no user Microsoft account to sign in with. The Graph provider is
implemented and covered by unit tests against a mocked `httpx` transport (`tests/unit/
test_calendar_provider.py`), and by a scenario test using the ICS/mock fallback. See the final
handoff report for the explicit "implemented, awaiting credentials" status — no live Graph call
has been made from this session.
