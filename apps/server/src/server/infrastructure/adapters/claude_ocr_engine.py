import base64
from typing import Any

import anthropic

from server.domain.entities import DocumentType
from server.domain.ports import DocumentContent

_EXTRACT_TOOL_NAME = "record_extracted_fields"


class ClaudeOcrEngine:
    """OcrEngine adapter backed by Claude's vision + structured tool-use output."""

    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def extract(self, content: DocumentContent, document_type: DocumentType) -> dict[str, Any]:
        response = self._client.messages.create(
            model=self._model,
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

        for block in response.content:
            if block.type == "tool_use" and block.name == _EXTRACT_TOOL_NAME:
                return block.input
        msg = "Claude did not return the expected extraction tool call"
        raise RuntimeError(msg)
