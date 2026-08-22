# Mail Docket (local app)

Review the work threads you haven't answered and send the replies — one button,
one confirmation.

This runs on your own machine and talks to Microsoft Graph directly with your
credentials. That's the whole point: the published Artifact version can't send,
because sending through it requires a per-send approval that a web page has no
way to request. Here there's no intermediary, so the button works.

## One-time setup

### 1. Register an app in Azure

You need a client ID so MSAL can sign you in. In the
[Azure portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations**:

1. **New registration**
   - Name: `Ametalis Mail Docket`
   - Supported account types: *Accounts in this organizational directory only*
   - Redirect URI: leave blank
2. Open the new app → **Authentication** → enable
   **Allow public client flows** = *Yes*. (Device-code sign-in needs this.)
3. **API permissions** → **Add a permission** → **Microsoft Graph** →
   **Delegated permissions** → add `Mail.Send` and `Mail.Read`.
4. If your tenant requires admin consent for these, click
   **Grant admin consent** (or ask whoever administers your tenant).
5. From **Overview**, copy the **Application (client) ID** and
   **Directory (tenant) ID**.

> If your tenant blocks `Mail.Send` for new registrations, sending will fail
> with a clear 403 from Microsoft rather than silently — see Troubleshooting.

### 2. Point the app at it

```bash
export GRAPH_CLIENT_ID="<application (client) id>"
export GRAPH_TENANT_ID="<directory (tenant) id>"
```

Put those in your shell profile so they persist, or use a `.env` you source.

### 3. Install and run

```bash
pip install -r mailops/requirements.txt
streamlit run mailops/app.py
```

The first run shows a code — open <https://microsoft.com/devicelogin>, enter it,
sign in, then press **Continue**. The token is cached in
`mailops/.msal_token_cache.json` (gitignored, owner-readable only), so later runs
sign you in silently.

## Using it

Each thread shows why it was flagged and what the other side actually asked.
The draft is editable — change it before sending if you want. **Send reply**
arms it, **Confirm & send** does it. A sent item turns green and drops out of
the open count.

## Troubleshooting

**"Missing environment variable(s)"** — the two exports above aren't set in the
shell you launched Streamlit from.

**Connection error / "Is Streamlit still running?"** — the browser lost the
server. Check the terminal: a traceback means the script crashed, no output
means the process stopped. Restart with `streamlit run mailops/app.py`.

**403 from Microsoft** — your tenant policy doesn't allow this app to send.
That's an Azure consent question, not a bug here; the message shown includes
Microsoft's own explanation.

**401 / sign-in expired** — delete `mailops/.msal_token_cache.json` and sign in
again.

## Notes

This directory is deliberately outside `src/sophie/`. Sophie is a health,
training and performance system; mail triage is a separate concern and doesn't
belong in its domain model or its architecture boundaries.

`docket_data.py` currently holds the three open threads as plain data. The
natural next step is generating it from a live mailbox scan instead of
maintaining it by hand.
