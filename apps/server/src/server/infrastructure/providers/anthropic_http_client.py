"""Single place where this package talks HTTP to the Anthropic Messages API.

Kept as plain functions (no error classification, no retries) so every caller
of `AIProvider` shares the same URL/headers/auth logic without repeating it,
while each caller is still free to handle failures/timeouts its own way.
"""

import os
from collections.abc import Iterable
from typing import Literal

import httpx

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

ANTHROPIC_VERSION = "2023-06-01"

# Betas that unlock the Claude Code / OAuth / caching capabilities. Only sent
# when authenticating with a Claude Code OAuth token — an ANTHROPIC_API_KEY
# request has no use for them.
CLAUDE_CODE_BETAS: tuple[str, ...] = (
    "claude-code-20250219",
    "oauth-2025-04-20",
    "interleaved-thinking-2025-05-14",
    "context-management-2025-06-27",
    "prompt-caching-scope-2026-01-05",
    "extended-cache-ttl-2025-04-11",
)

# A Claude Code OAuth token is only accepted by the Messages API when the
# first `system` block identifies the caller as Claude Code — every request
# authenticated this way must prepend it (see `build_system_blocks`).
CLAUDE_CODE_SYSTEM_IDENTIFIER = "You are Claude Code, Anthropic's official CLI for Claude."

AuthMode = Literal["oauth", "api_key"]


def get_auth_mode() -> AuthMode:
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return "oauth"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "api_key"
    msg = "No auth configured: set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY"
    raise RuntimeError(msg)


def build_anthropic_auth_header(mode: AuthMode | None = None) -> dict[str, str]:
    mode = mode or get_auth_mode()
    if mode == "oauth":
        return {"Authorization": f"Bearer {os.environ['CLAUDE_CODE_OAUTH_TOKEN']}"}
    return {"x-api-key": os.environ["ANTHROPIC_API_KEY"]}


def build_anthropic_headers(
    extra_betas: Iterable[str] = (),
    version: str = ANTHROPIC_VERSION,
) -> dict[str, str]:
    mode = get_auth_mode()
    base_betas = CLAUDE_CODE_BETAS if mode == "oauth" else ()
    betas = dict.fromkeys((*base_betas, *extra_betas))

    headers = {
        "content-type": "application/json",
        "anthropic-version": version,
        **build_anthropic_auth_header(mode),
    }
    if betas:
        headers["anthropic-beta"] = ",".join(betas)
    return headers


def build_system_blocks(system: str) -> str | list[dict[str, str]]:
    """Wraps `system` for the wire format expected by the active auth mode.

    A Claude Code OAuth token requires the identifying block first; an
    ANTHROPIC_API_KEY request has no such requirement and can send a plain
    string.
    """
    if get_auth_mode() == "oauth":
        return [
            {"type": "text", "text": CLAUDE_CODE_SYSTEM_IDENTIFIER},
            {"type": "text", "text": system},
        ]
    return system


def request_anthropic_api(
    body: dict, headers: dict[str, str], client: httpx.Client
) -> httpx.Response:
    return client.post(ANTHROPIC_API_URL, headers=headers, json=body)
