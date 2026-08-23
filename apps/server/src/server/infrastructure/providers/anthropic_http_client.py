"""Single place where this package talks HTTP to the Anthropic Messages API.

Kept as plain functions (no error classification, no retries) so every caller
of `AIProvider` shares the same URL/headers/auth logic without repeating it,
while each caller is still free to handle failures/timeouts its own way.
"""

import os
from collections.abc import Iterable

import httpx

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

ANTHROPIC_VERSION = "2023-06-01"

# Default betas that unlock the Claude Code / OAuth / caching capabilities
# this project's Anthropic access relies on.
CLAUDE_CODE_BETAS: tuple[str, ...] = (
    "claude-code-20250219",
    "oauth-2025-04-20",
    "interleaved-thinking-2025-05-14",
    "context-management-2025-06-27",
    "prompt-caching-scope-2026-01-05",
    "extended-cache-ttl-2025-04-11",
)


def build_anthropic_auth_header() -> dict[str, str]:
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if oauth_token:
        return {"Authorization": f"Bearer {oauth_token}"}
    msg = "No auth configured: set CLAUDE_CODE_OAUTH_TOKEN"
    raise RuntimeError(msg)


def build_anthropic_headers(
    betas: Iterable[str] = CLAUDE_CODE_BETAS,
    extra_betas: Iterable[str] = (),
    version: str = ANTHROPIC_VERSION,
) -> dict[str, str]:
    all_betas = dict.fromkeys((*betas, *extra_betas))
    return {
        "content-type": "application/json",
        "anthropic-version": version,
        "anthropic-beta": ",".join(all_betas),
        **build_anthropic_auth_header(),
    }


def request_anthropic_api(
    body: dict, headers: dict[str, str], client: httpx.Client
) -> httpx.Response:
    return client.post(ANTHROPIC_API_URL, headers=headers, json=body)
