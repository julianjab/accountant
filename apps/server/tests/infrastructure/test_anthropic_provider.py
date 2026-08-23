import httpx
import pytest

from server.infrastructure.providers.anthropic_http_client import CLAUDE_CODE_SYSTEM_IDENTIFIER
from server.infrastructure.providers.anthropic_provider import AnthropicApiError, AnthropicProvider


def test_create_message_posts_body_with_claude_code_system_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["json"] = httpx.Response(200, content=request.content).json()
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
    assert captured["json"]["system"] == [
        {"type": "text", "text": CLAUDE_CODE_SYSTEM_IDENTIFIER},
        {"type": "text", "text": "be terse"},
    ]


def test_create_message_sends_plain_system_string_for_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = httpx.Response(200, content=request.content).json()
        return httpx.Response(200, json={"content": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(client=client)

    provider.create_message(
        model="claude-sonnet-5",
        system="be terse",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
    )

    assert captured["json"]["system"] == "be terse"


def test_create_message_raises_sanitized_error_without_leaking_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(client=client)

    with pytest.raises(AnthropicApiError) as excinfo:
        provider.create_message(
            model="claude-sonnet-5",
            system="be terse",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=64,
        )

    assert excinfo.value.status_code == 401
    assert "test-token" not in str(excinfo.value)
