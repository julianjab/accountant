import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from server.domain.entities import GoogleUser
from server.domain.ports import OAuthGrantRevoked, OAuthTokens, OAuthTransportError

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

SCOPES = "https://www.googleapis.com/auth/drive.readonly openid email profile"

_TIMEOUT = 30.0

_logger = logging.getLogger(__name__)


def _is_invalid_grant(response: httpx.Response) -> bool:
    try:
        return response.json().get("error") == "invalid_grant"
    except ValueError:
        return False


class GoogleGrantRevokedError(OAuthGrantRevoked):
    """Google reported ``invalid_grant``: the refresh token is dead."""


class GoogleOAuthError(OAuthTransportError):
    """A call to Google's OAuth endpoints failed.

    Carries no response body: Google echoes back client credentials in some error
    payloads, and this message reaches the browser.
    """


class HttpGoogleOAuthClient:
    """GoogleOAuthClient adapter for the authorization-code flow.

    Unlike the browser-side implicit flow, this one is confidential (it holds the
    client secret) and therefore receives a refresh token, which is what lets a
    session outlive the access token's hour.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            # Required to receive a refresh token: "offline" asks for one, and
            # "consent" forces re-issue even if the user already granted access.
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthTokens:
        return self._token_request(
            {
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri,
                "grant_type": "authorization_code",
            }
        )

    def refresh(self, refresh_token: str) -> OAuthTokens:
        return self._token_request(
            {
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
            }
        )

    def fetch_user(self, access_token: str) -> GoogleUser:
        try:
            response = httpx.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Failed to fetch the Google user profile") from exc

        payload = response.json()
        if not payload.get("email_verified", False):
            # An unverified email can be anything; the allowlist keys on it.
            raise GoogleOAuthError("The Google account has no verified email")

        return GoogleUser(
            email=payload["email"],
            name=payload.get("name", payload["email"]),
            picture=payload.get("picture"),
        )

    def revoke(self, token: str) -> None:
        try:
            httpx.post(REVOKE_URL, data={"token": token}, timeout=_TIMEOUT).raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Failed to revoke the Google grant") from exc

    def _token_request(self, data: dict[str, str]) -> OAuthTokens:
        try:
            response = httpx.post(TOKEN_URL, data=data, timeout=_TIMEOUT)
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Could not reach Google's token endpoint") from exc

        if response.status_code in (400, 401) and _is_invalid_grant(response):
            raise GoogleGrantRevokedError("The Google grant is no longer valid")

        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # Logged, never returned: Google echoes client credentials in some
            # error payloads and this message reaches the browser.
            _logger.error(
                "Google rejected the token request (%s): %s",
                response.status_code,
                response.text,
            )
            raise GoogleOAuthError("Google rejected the token request") from exc

        payload = response.json()
        expires_in = int(payload.get("expires_in", 3600))
        return OAuthTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            granted_scopes=frozenset(payload.get("scope", "").split()),
        )
