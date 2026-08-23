from typing import Any

import httpx

from server.infrastructure.providers.anthropic_http_client import (
    build_anthropic_headers,
    request_anthropic_api,
)


class AnthropicProvider:
    """AIProvider adapter that calls the Anthropic Messages API directly over
    HTTP (no SDK), authenticating with a Claude Code OAuth token."""

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
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools is not None:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice

        response = request_anthropic_api(body, build_anthropic_headers(), self._client)
        response.raise_for_status()
        return response.json()
