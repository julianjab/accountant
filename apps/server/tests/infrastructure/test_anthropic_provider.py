import httpx
import pytest

from server.infrastructure.providers.anthropic_provider import AnthropicProvider


def test_create_message_posts_body_and_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(client=client)

    result = provider.create_message(
        model="claude-sonnet-5",
        system="be terse",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
    )

    assert result == {"content": [{"type": "text", "text": "ok"}]}
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["authorization"] == "Bearer test-token"


def test_create_message_raises_on_error_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(client=client)

    with pytest.raises(httpx.HTTPStatusError):
        provider.create_message(
            model="claude-sonnet-5",
            system="be terse",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=64,
        )
