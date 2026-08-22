import base64

import anthropic

from server.domain.ports import DocumentContent, ProposedOcrConfig

_PROPOSE_TOOL_NAME = "propose_ocr_config"


class ClaudeDocumentTypeConfigurator:
    """DocumentTypeConfigurator adapter: Claude inspects a sample document and
    proposes the extraction prompt + JSON schema to use for that document type."""

    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def propose_config(self, content: DocumentContent, type_name: str) -> ProposedOcrConfig:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            tools=[
                {
                    "name": _PROPOSE_TOOL_NAME,
                    "description": "Propose the OCR extraction prompt and JSON schema for this "
                    "document type.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "extraction_prompt": {
                                "type": "string",
                                "description": "Instructions to extract this document "
                                "type's fields.",
                            },
                            "extraction_schema": {
                                "type": "object",
                                "description": "JSON Schema (as an object) describing "
                                "the fields to extract.",
                            },
                        },
                        "required": ["extraction_prompt", "extraction_schema"],
                    },
                }
            ],
            tool_choice={"type": "tool", "name": _PROPOSE_TOOL_NAME},
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
                        {
                            "type": "text",
                            "text": (
                                f'This is a sample "{type_name}" document. Design an extraction '
                                "prompt and a JSON Schema covering every relevant field in it, so "
                                "future documents of this same type can be OCR'd consistently."
                            ),
                        },
                    ],
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == _PROPOSE_TOOL_NAME:
                return ProposedOcrConfig(
                    extraction_prompt=block.input["extraction_prompt"],
                    extraction_schema=block.input["extraction_schema"],
                )
        msg = "Claude did not return the expected config proposal tool call"
        raise RuntimeError(msg)
