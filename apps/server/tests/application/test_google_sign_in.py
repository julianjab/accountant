from datetime import UTC, datetime, timedelta

import pytest

from server.application.use_cases import (
    CompleteGoogleSignIn,
    GetGoogleSession,
    MissingRefreshToken,
    SignOutGoogle,
)
from server.domain.entities import GoogleUser
from server.domain.ports import OAuthTokens
from server.infrastructure.adapters.in_memory_repositories import InMemorySessionRepository

USER = GoogleUser(email="a@b.com", name="A B", picture=None)


class FakeOAuth:
    def __init__(self, tokens: OAuthTokens, refreshed: OAuthTokens | None = None) -> None:
        self._tokens = tokens
        self._refreshed = refreshed
        self.revoked: list[str] = []
        self.refresh_calls = 0

    def authorization_url(self, state: str) -> str:
        return f"https://accounts.google.com/auth?state={state}"

    def exchange_code(self, code: str) -> OAuthTokens:
        return self._tokens

    def refresh(self, refresh_token: str) -> OAuthTokens:
        self.refresh_calls += 1
        if self._refreshed is None:
            raise RuntimeError("grant revoked")
        return self._refreshed

    def fetch_user(self, access_token: str) -> GoogleUser:
        return USER

    def revoke(self, token: str) -> None:
        self.revoked.append(token)


def tokens(access: str, refresh: str | None, ttl_seconds: int) -> OAuthTokens:
    return OAuthTokens(
        access_token=access,
        refresh_token=refresh,
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
    )


def test_sign_in_persists_the_session():
    sessions = InMemorySessionRepository()
    use_case = CompleteGoogleSignIn(FakeOAuth(tokens("at", "rt", 3600)), sessions)

    session = use_case.execute("code")

    assert session.user == USER
    assert sessions.get(session.id) == session


def test_sign_in_rejects_a_grant_without_a_refresh_token():
    sessions = InMemorySessionRepository()
    use_case = CompleteGoogleSignIn(FakeOAuth(tokens("at", None, 3600)), sessions)

    with pytest.raises(MissingRefreshToken):
        use_case.execute("code")


def test_valid_session_is_returned_without_refreshing():
    sessions = InMemorySessionRepository()
    oauth = FakeOAuth(tokens("at", "rt", 3600))
    session = CompleteGoogleSignIn(oauth, sessions).execute("code")

    loaded = GetGoogleSession(oauth, sessions).execute(session.id)

    assert loaded is not None
    assert loaded.access_token == "at"
    assert oauth.refresh_calls == 0


def test_expired_session_is_refreshed_and_stored():
    sessions = InMemorySessionRepository()
    oauth = FakeOAuth(tokens("old", "rt", -1), refreshed=tokens("new", None, 3600))
    session = CompleteGoogleSignIn(oauth, sessions).execute("code")

    loaded = GetGoogleSession(oauth, sessions).execute(session.id)

    assert loaded is not None
    assert loaded.access_token == "new"
    # Google omits the refresh token on renewal, so the stored one must survive.
    assert loaded.refresh_token == "rt"
    assert sessions.get(session.id).access_token == "new"


def test_session_is_dropped_when_the_refresh_fails():
    sessions = InMemorySessionRepository()
    oauth = FakeOAuth(tokens("old", "rt", -1), refreshed=None)
    session = CompleteGoogleSignIn(oauth, sessions).execute("code")

    assert GetGoogleSession(oauth, sessions).execute(session.id) is None
    assert sessions.get(session.id) is None


def test_unknown_session_id_returns_none():
    sessions = InMemorySessionRepository()
    assert GetGoogleSession(FakeOAuth(tokens("at", "rt", 3600)), sessions).execute("nope") is None


def test_sign_out_deletes_the_session_and_revokes_the_grant():
    sessions = InMemorySessionRepository()
    oauth = FakeOAuth(tokens("at", "rt", 3600))
    session = CompleteGoogleSignIn(oauth, sessions).execute("code")

    SignOutGoogle(oauth, sessions).execute(session.id)

    assert sessions.get(session.id) is None
    assert oauth.revoked == ["rt"]
