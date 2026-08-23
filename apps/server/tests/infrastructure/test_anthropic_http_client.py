import pytest

from server.infrastructure.providers.anthropic_http_client import (
    CLAUDE_CODE_BETAS,
    build_anthropic_auth_header,
    build_anthropic_headers,
)


def test_build_anthropic_auth_header_uses_oauth_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")

    assert build_anthropic_auth_header() == {"Authorization": "Bearer test-token"}


def test_build_anthropic_auth_header_raises_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN"):
        build_anthropic_auth_header()


def test_build_anthropic_headers_merges_default_and_extra_betas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")

    headers = build_anthropic_headers(extra_betas=["task-budgets-2026-03-13"])

    betas = headers["anthropic-beta"].split(",")
    assert betas[: len(CLAUDE_CODE_BETAS)] == list(CLAUDE_CODE_BETAS)
    assert "task-budgets-2026-03-13" in betas
    assert headers["Authorization"] == "Bearer test-token"
