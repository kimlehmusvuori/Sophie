"""Microsoft Graph access for the mail docket.

Authentication uses MSAL's device-code flow: the app prints a short code, the
user signs in at microsoft.com/devicelogin in any browser, and the resulting
token is cached on disk so subsequent runs are silent.

This talks to Graph directly with the user's own delegated credentials. It does
not go through any intermediary, which is why sending works here and not from a
published Artifact page.
"""

from __future__ import annotations

import atexit
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
import msal

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Send", "Mail.Read"]

# Cache lives beside the app and is gitignored — it holds a refresh token.
TOKEN_CACHE_PATH = Path(__file__).with_name(".msal_token_cache.json")


class GraphError(RuntimeError):
    """Raised when Graph rejects a request. `status` is the HTTP status code."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class GraphConfig:
    client_id: str
    tenant_id: str

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"


def load_config() -> GraphConfig:
    """Read the Azure app registration details from the environment."""
    client_id = os.environ.get("GRAPH_CLIENT_ID", "").strip()
    tenant_id = os.environ.get("GRAPH_TENANT_ID", "").strip()

    missing = [
        name
        for name, value in (("GRAPH_CLIENT_ID", client_id), ("GRAPH_TENANT_ID", tenant_id))
        if not value
    ]
    if missing:
        raise GraphError(
            "Missing environment variable(s): "
            + ", ".join(missing)
            + ". See mailops/README.md for how to create the app registration."
        )
    return GraphConfig(client_id=client_id, tenant_id=tenant_id)


def _build_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())

    def _persist() -> None:
        if cache.has_state_changed:
            TOKEN_CACHE_PATH.write_text(cache.serialize())
            # Refresh token on disk — keep it owner-only.
            try:
                TOKEN_CACHE_PATH.chmod(0o600)
            except OSError:
                pass

    atexit.register(_persist)
    return cache


def build_app(config: GraphConfig) -> msal.PublicClientApplication:
    """Construct the MSAL client.

    MSAL contacts the authority during construction to discover the tenant's
    OIDC configuration, so a wrong tenant id or no network raises here — as a
    bare ValueError. Translate it, otherwise the caller sees a stack trace
    instead of the one sentence that tells them what to fix.
    """
    try:
        return msal.PublicClientApplication(
            client_id=config.client_id,
            authority=config.authority,
            token_cache=_build_cache(),
        )
    except ValueError as exc:
        detail = str(exc)
        if "invalid_tenant" in detail or "not found" in detail:
            raise GraphError(
                f"Microsoft does not recognise tenant '{config.tenant_id}'. "
                "Check GRAPH_TENANT_ID against Directory (tenant) ID in the Azure portal."
            ) from exc
        raise GraphError(f"Could not reach Microsoft sign-in: {detail}") from exc
    except Exception as exc:  # network stack, DNS, proxy failures
        raise GraphError(
            f"Could not reach Microsoft sign-in ({exc.__class__.__name__}: {exc}). "
            "Check your network connection."
        ) from exc


def acquire_token_silent(app: msal.PublicClientApplication) -> str | None:
    """Return a cached access token, or None if the user must sign in."""
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        return str(result["access_token"])
    return None


def begin_device_flow(app: msal.PublicClientApplication) -> dict:
    """Start device-code sign-in. The returned dict carries the user code."""
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise GraphError(
            "Could not start device sign-in: " + flow.get("error_description", "unknown error")
        )
    return flow


def complete_device_flow(app: msal.PublicClientApplication, flow: dict) -> str:
    """Block until the user finishes signing in, then return an access token."""
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise GraphError(
            "Sign-in did not complete: " + result.get("error_description", "unknown error")
        )
    return str(result["access_token"])


def signed_in_as(token: str) -> str:
    """Return the mailbox address the token belongs to."""
    response = httpx.get(
        f"{GRAPH_ROOT}/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if response.status_code != 200:
        raise GraphError(_describe(response), response.status_code)
    payload = response.json()
    return str(payload.get("mail") or payload.get("userPrincipalName") or "unknown")


def send_mail(
    token: str,
    *,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
) -> None:
    """Send a plain-text message as the signed-in user.

    Graph returns 202 Accepted with an empty body on success. Any other status
    raises GraphError with the service's own explanation, so the caller can show
    the real reason rather than a generic failure.
    """
    message: dict = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": address}} for address in to],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": address}} for address in cc]

    response = httpx.post(
        f"{GRAPH_ROOT}/me/sendMail",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"message": message, "saveToSentItems": True},
        timeout=30,
    )
    if response.status_code not in (200, 202):
        raise GraphError(_describe(response), response.status_code)


def _describe(response: httpx.Response) -> str:
    """Turn a Graph error response into something worth showing a human."""
    try:
        error = response.json().get("error", {})
        code = error.get("code", "")
        message = error.get("message", "")
        detail = " — ".join(part for part in (code, message) if part)
    except ValueError:
        detail = response.text[:300]

    if response.status_code == 401:
        return "Sign-in expired or was revoked. Sign in again. " + detail
    if response.status_code == 403:
        return (
            "Microsoft refused the request: your account or tenant policy does not permit "
            "sending this way. " + detail
        )
    if response.status_code == 429:
        return "Throttled by Microsoft — wait a moment and try again. " + detail
    return f"Graph returned HTTP {response.status_code}. {detail}"
