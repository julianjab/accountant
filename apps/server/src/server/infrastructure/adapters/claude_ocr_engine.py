import base64
from typing import Any

from server.domain.entities import DocumentType
from server.domain.ports import DocumentContent
from server.infrastructure.config.prompts import PromptSpec
from server.infrastructure.providers.ai_provider import AIProvider

_EXTRACT_TOOL_NAME = "record_extracted_fields"


class ClaudeOcrEngine:
    """OcrEngine adapter backed by Claude's vision + structured tool-use output."""

    def __init__(self, provider: AIProvider, model: str, prompt: PromptSpec) -> None:
        self._provider = provider
        self._model = model
        self._prompt = prompt

    def extract(self, content: DocumentContent, document_type: DocumentType) -> dict[str, Any]:
        response = self._provider.create_message(
            model=self._model,
            system=self._prompt.system,
            max_tokens=4096,
            tools=[
                {
                    "name": _EXTRACT_TOOL_NAME,
                    "description": "Record the fields extracted from the document.",
                    "input_schema": document_type.extraction_schema,
                }
            ],
            tool_choice={"type": "tool", "name": _EXTRACT_TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document"
                            if content.mime_type == "application/pdf"
                            else "image",
                            "source": {
                                "type": "base64",
                                "media_type": content.mime_type,
                                "data": base64.b64encode(content.data).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": document_type.extraction_prompt},
                    ],
                }
            ],
        )

        for block in response["content"]:
            if block["type"] == "tool_use" and block["name"] == _EXTRACT_TOOL_NAME:
                return block["input"]
        msg = "Claude did not return the expected extraction tool call"
        raise RuntimeError(msg)
