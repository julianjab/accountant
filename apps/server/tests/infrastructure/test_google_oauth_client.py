from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from server.infrastructure.adapters.google_oauth_client import (
    GoogleGrantRevokedError,
    GoogleOAuthError,
    HttpGoogleOAuthClient,
)

CLIENT = HttpGoogleOAuthClient(
    client_id="cid", client_secret="secret", redirect_uri="http://localhost:8000/cb"
)


class FakeResponse:
    def __init__(self, payload: dict, error: bool = False, status_code: int = 200) -> None:
        self._payload = payload
        self._error = error
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self._error:
            raise httpx.HTTPError("boom")

    def json(self) -> dict:
        return self._payload


def test_authorization_url_asks_for_an_offline_grant():
    url = CLIENT.authorization_url("state-123")
    params = parse_qs(urlparse(url).query)

    # Without both of these Google returns no refresh token, and the session
    # cannot outlive the access token.
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    assert params["state"] == ["state-123"]
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["cid"]
    assert "drive.readonly" in params["scope"][0]


def test_exchange_code_returns_tokens_with_an_absolute_expiry(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResponse({"access_token": "at", "refresh_token": "rt", "expires_in": 60})

    monkeypatch.setattr(httpx, "post", fake_post)
    before = datetime.now(UTC)

    tokens = CLIENT.exchange_code("code-1")

    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["client_secret"] == "secret"
    assert tokens.access_token == "at"
    assert tokens.refresh_token == "rt"
    assert 59 <= (tokens.expires_at - before).total_seconds() <= 61


def test_refresh_uses_the_refresh_grant_and_tolerates_a_missing_refresh_token(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["data"] = data
        return FakeResponse({"access_token": "new"})

    monkeypatch.setattr(httpx, "post", fake_post)

    tokens = CLIENT.refresh("rt")

    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["refresh_token"] == "rt"
    assert tokens.access_token == "new"
    assert tokens.refresh_token is None


def test_token_request_failure_does_not_leak_the_response(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: FakeResponse({"error": "invalid_client"}, error=True, status_code=403),
    )

    with pytest.raises(GoogleOAuthError) as exc:
        CLIENT.exchange_code("code-1")

    assert "invalid_client" not in str(exc.value)


def test_a_dead_refresh_token_is_reported_as_a_revoked_grant(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: FakeResponse({"error": "invalid_grant"}, error=True, status_code=400),
    )

    with pytest.raises(GoogleGrantRevokedError):
        CLIENT.refresh("rt")


def test_a_transport_failure_is_not_mistaken_for_a_revoked_grant(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "post", boom)

    with pytest.raises(GoogleOAuthError) as exc:
        CLIENT.refresh("rt")

    # A timeout must never cost the user their grant.
    assert not isinstance(exc.value, GoogleGrantRevokedError)


def test_fetch_user_maps_the_profile(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse(
            {"email": "a@b.com", "name": "A B", "picture": "p.png", "email_verified": True}
        ),
    )

    user = CLIENT.fetch_user("at")

    assert user.email == "a@b.com"
    assert user.name == "A B"
    assert user.picture == "p.png"


def test_fetch_user_falls_back_to_the_email_when_no_name_is_returned(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse({"email": "a@b.com", "email_verified": True})
    )

    user = CLIENT.fetch_user("at")

    assert user.name == "a@b.com"
    assert user.picture is None


def test_fetch_user_failure_raises(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse({}, error=True))

    with pytest.raises(GoogleOAuthError):
        CLIENT.fetch_user("at")


def test_revoke_posts_the_token(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResponse({})

    monkeypatch.setattr(httpx, "post", fake_post)

    CLIENT.revoke("rt")

    assert captured["data"] == {"token": "rt"}


def test_revoke_failure_raises(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse({}, error=True))

    with pytest.raises(GoogleOAuthError):
        CLIENT.revoke("rt")


def test_an_unverified_email_is_rejected(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse({"email": "a@b.com", "email_verified": False}),
    )

    # The allowlist keys on the email, so an unverified one must not be trusted.
    with pytest.raises(GoogleOAuthError):
        CLIENT.fetch_user("at")
