"""AIProvider: the low-level abstraction the Claude-backed adapters
(ClaudeDocumentClassifier, ClaudeOcrEngine, ClaudeDocumentTypeConfigurator)
build on to talk to a messages API. It lives in infrastructure, not
domain/ports, because it's a transport-detail abstraction (wire format,
auth, tool-use shape) shared across adapters — not a business capability a
use case depends on. Swapping the LLM vendor means adding a new
implementation here, without touching the domain ports or the use cases.
"""

from typing import Any, Protocol


class AIProvider(Protocol):
    def create_message(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
