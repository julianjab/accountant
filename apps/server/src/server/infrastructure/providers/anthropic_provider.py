from typing import Any

import httpx

from server.infrastructure.providers.anthropic_http_client import (
    build_anthropic_headers,
    build_system_blocks,
    request_anthropic_api,
)


class AnthropicApiError(RuntimeError):
    """Raised on a non-2xx Anthropic API response.

    Deliberately doesn't carry the underlying `httpx.Request`/response
    objects (unlike `httpx.HTTPStatusError`) — those hold the auth header,
    and a logger that serializes the raw exception would leak it.
    """

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Anthropic API request failed with status {status_code}: {body}")
        self.status_code = status_code


class AnthropicProvider:
    """AIProvider adapter that calls the Anthropic Messages API directly over
    HTTP (no SDK), authenticating with a Claude Code OAuth token or a plain
    ANTHROPIC_API_KEY — whichever is set in the environment."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=120.0)

    def create_message(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "system": build_system_blocks(system),
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools is not None:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice

        response = request_anthropic_api(body, build_anthropic_headers(), self._client)
        if response.is_error:
            raise AnthropicApiError(response.status_code, response.text)
        return response.json()
