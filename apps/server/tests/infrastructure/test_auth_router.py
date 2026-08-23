from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import GoogleUser
from server.domain.ports import OAuthTokens
from server.infrastructure.adapters.google_oauth_client import GoogleOAuthError
from server.infrastructure.adapters.in_memory_repositories import InMemorySessionRepository
from server.infrastructure.api import deps
from server.infrastructure.api.routers.auth import SESSION_COOKIE, STATE_COOKIE
from server.main import app

USER = GoogleUser(email="a@b.com", name="A B", picture=None)
WEB_APP_URL = "http://localhost:3000"


class FakeOAuth:
    def __init__(self, refresh_token: str | None = "rt", exchange_error: bool = False) -> None:
        self._refresh_token = refresh_token
        self._exchange_error = exchange_error
        self.revoked: list[str] = []

    def authorization_url(self, state: str) -> str:
        return f"https://accounts.google.com/auth?state={state}"

    def exchange_code(self, code: str) -> OAuthTokens:
        if self._exchange_error:
            raise GoogleOAuthError("rejected")
        return OAuthTokens(
            access_token="at",
            refresh_token=self._refresh_token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    def refresh(self, refresh_token: str) -> OAuthTokens:
        raise AssertionError("not expected in these tests")

    def fetch_user(self, access_token: str) -> GoogleUser:
        return USER

    def revoke(self, token: str) -> None:
        self.revoked.append(token)


@pytest.fixture
def sessions():
    return InMemorySessionRepository()


@pytest.fixture
def oauth():
    return FakeOAuth()


@pytest.fixture(autouse=True)
def anthropic_auth(monkeypatch):
    # The app's lifespan fails fast when no AI auth is configured.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def client(sessions, oauth):
    app.dependency_overrides[deps.get_session_repository] = lambda: sessions
    app.dependency_overrides[deps.get_google_oauth_client] = lambda: oauth
    # The use-case providers build their own collaborators, so override them too.
    from server.application.use_cases import (
        CompleteGoogleSignIn,
        GetGoogleSession,
        SignOutGoogle,
    )

    app.dependency_overrides[deps.get_complete_google_sign_in_use_case] = lambda: (
        CompleteGoogleSignIn(oauth, sessions, lambda _email: True)
    )
    app.dependency_overrides[deps.get_google_session_use_case] = lambda: GetGoogleSession(
        oauth, sessions, timedelta(days=30)
    )
    app.dependency_overrides[deps.get_sign_out_google_use_case] = lambda: SignOutGoogle(
        oauth, sessions
    )

    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def configure_oauth(monkeypatch):
    settings = deps.get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", "cid")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "secret")
    monkeypatch.setattr(settings, "web_app_url", WEB_APP_URL)


def test_login_redirects_to_google_and_stores_the_state(client, monkeypatch):
    configure_oauth(monkeypatch)

    response = client.get("/auth/google/login")

    assert response.status_code == 307
    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    assert client.cookies[STATE_COOKIE] == state


def test_login_fails_loudly_when_oauth_is_not_configured(client, monkeypatch):
    settings = deps.get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", "")

    assert client.get("/auth/google/login").status_code == 500


def test_callback_establishes_a_session(client, sessions, monkeypatch):
    configure_oauth(monkeypatch)
    client.cookies.set(STATE_COOKIE, "s1")

    response = client.get("/auth/google/callback", params={"code": "c", "state": "s1"})

    assert response.status_code == 307
    assert response.headers["location"] == WEB_APP_URL
    session_id = client.cookies[SESSION_COOKIE]
    assert sessions.get(session_id).user == USER


def test_callback_rejects_a_mismatched_state(client, sessions, monkeypatch):
    configure_oauth(monkeypatch)
    client.cookies.set(STATE_COOKIE, "s1")

    response = client.get("/auth/google/callback", params={"code": "c", "state": "forged"})

    assert response.headers["location"] == f"{WEB_APP_URL}?auth_error=state"
    assert SESSION_COOKIE not in client.cookies


def test_callback_reports_a_denied_consent(client, monkeypatch):
    configure_oauth(monkeypatch)

    response = client.get("/auth/google/callback", params={"error": "access_denied"})

    assert response.headers["location"] == f"{WEB_APP_URL}?auth_error=denied"


def test_callback_reports_a_grant_without_a_refresh_token(sessions, monkeypatch):
    oauth = FakeOAuth(refresh_token=None)
    from server.application.use_cases import CompleteGoogleSignIn

    app.dependency_overrides[deps.get_complete_google_sign_in_use_case] = lambda: (
        CompleteGoogleSignIn(oauth, sessions, lambda _email: True)
    )
    configure_oauth(monkeypatch)

    with TestClient(app, follow_redirects=False) as test_client:
        test_client.cookies.set(STATE_COOKIE, "s1")
        response = test_client.get("/auth/google/callback", params={"code": "c", "state": "s1"})

    assert response.headers["location"] == f"{WEB_APP_URL}?auth_error=no_refresh"
    app.dependency_overrides.clear()


def test_callback_reports_a_failed_exchange(sessions, monkeypatch):
    oauth = FakeOAuth(exchange_error=True)
    from server.application.use_cases import CompleteGoogleSignIn

    app.dependency_overrides[deps.get_complete_google_sign_in_use_case] = lambda: (
        CompleteGoogleSignIn(oauth, sessions, lambda _email: True)
    )
    configure_oauth(monkeypatch)

    with TestClient(app, follow_redirects=False) as test_client:
        test_client.cookies.set(STATE_COOKIE, "s1")
        response = test_client.get("/auth/google/callback", params={"code": "c", "state": "s1"})

    assert response.headers["location"] == f"{WEB_APP_URL}?auth_error=exchange"
    app.dependency_overrides.clear()


def test_me_requires_a_session_cookie(client):
    assert client.get("/auth/google/me").status_code == 401


def test_me_rejects_an_unknown_session(client):
    client.cookies.set(SESSION_COOKIE, "nope")

    assert client.get("/auth/google/me").status_code == 401


def test_me_returns_the_signed_in_user(client, monkeypatch):
    configure_oauth(monkeypatch)
    client.cookies.set(STATE_COOKIE, "s1")
    client.get("/auth/google/callback", params={"code": "c", "state": "s1"})

    response = client.get("/auth/google/me")

    assert response.status_code == 200
    assert response.json() == {"email": "a@b.com", "name": "A B", "picture": None}


def test_logout_clears_the_session_and_revokes_the_grant(client, sessions, oauth, monkeypatch):
    configure_oauth(monkeypatch)
    client.cookies.set(STATE_COOKIE, "s1")
    client.get("/auth/google/callback", params={"code": "c", "state": "s1"})
    session_id = client.cookies[SESSION_COOKIE]

    response = client.post("/auth/google/logout")

    assert response.status_code == 204
    assert sessions.get(session_id) is None
    assert oauth.revoked == ["rt"]


def test_logout_without_a_session_is_a_no_op(client):
    assert client.post("/auth/google/logout").status_code == 204
