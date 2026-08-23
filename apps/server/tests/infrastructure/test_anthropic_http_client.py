import pytest

from server.infrastructure.providers.anthropic_http_client import (
    CLAUDE_CODE_BETAS,
    CLAUDE_CODE_SYSTEM_IDENTIFIER,
    build_anthropic_auth_header,
    build_anthropic_headers,
    build_system_blocks,
    get_auth_mode,
)


def _clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_get_auth_mode_prefers_api_key_over_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "api-key")

    assert get_auth_mode() == "api_key"


def test_get_auth_mode_falls_back_to_oauth_without_an_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token")

    assert get_auth_mode() == "oauth"


def test_get_auth_mode_raises_without_any_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN"):
        get_auth_mode()


def test_oauth_auth_header_and_betas(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token")

    assert build_anthropic_auth_header() == {"Authorization": "Bearer oauth-token"}

    headers = build_anthropic_headers(extra_betas=["task-budgets-2026-03-13"])
    betas = headers["anthropic-beta"].split(",")
    assert betas[: len(CLAUDE_CODE_BETAS)] == list(CLAUDE_CODE_BETAS)
    assert "task-budgets-2026-03-13" in betas


def test_api_key_auth_header_sends_no_claude_code_betas(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    assert build_anthropic_auth_header() == {"x-api-key": "sk-test"}

    headers = build_anthropic_headers()
    assert "anthropic-beta" not in headers


def test_build_system_blocks_prepends_identifier_only_for_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token")

    assert build_system_blocks("classify this") == [
        {"type": "text", "text": CLAUDE_CODE_SYSTEM_IDENTIFIER},
        {"type": "text", "text": "classify this"},
    ]

    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    assert build_system_blocks("classify this") == "classify this"
