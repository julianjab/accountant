from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from server.domain.entities import GoogleUser


@dataclass(frozen=True, slots=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    granted_scopes: frozenset[str] = frozenset()


class OAuthTransportError(Exception):
    """A call to the OAuth provider failed.

    Declared here so every adapter raises the same type and callers are not
    coupled to a particular implementation.
    """


class OAuthGrantRevoked(OAuthTransportError):
    """The refresh token is no longer valid and re-consent is required.

    Distinct from a transport failure on purpose: only this one justifies
    dropping a stored session. A timeout must never cost the user their grant.
    """


class DriveAccessNotGranted(Exception):
    """The user signed in but withheld Drive access.

    Google returns the granted scopes rather than failing, so without this the
    app would hold a session that cannot read a single document.
    """


class GoogleOAuthClient(Protocol):
    def authorization_url(self, state: str) -> str: ...
    def exchange_code(self, code: str) -> OAuthTokens: ...
    def refresh(self, refresh_token: str) -> OAuthTokens: ...
    def fetch_user(self, access_token: str) -> GoogleUser: ...
    def revoke(self, token: str) -> None: ...
