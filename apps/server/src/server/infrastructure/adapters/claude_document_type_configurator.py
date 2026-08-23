import base64

from server.domain.ports import DocumentContent, ProposedOcrConfig
from server.infrastructure.config.prompts import TemplatedPrompt
from server.infrastructure.providers.ai_provider import AIProvider

_PROPOSE_TOOL_NAME = "propose_ocr_config"


class ClaudeDocumentTypeConfigurator:
    """DocumentTypeConfigurator adapter: Claude inspects a sample document and
    proposes the extraction prompt + JSON schema to use for that document type."""

    def __init__(self, provider: AIProvider, model: str, prompt: TemplatedPrompt) -> None:
        self._provider = provider
        self._model = model
        self._prompt = prompt

    def propose_config(self, content: DocumentContent, type_name: str) -> ProposedOcrConfig:
        response = self._provider.create_message(
            model=self._model,
            system=self._prompt.system,
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
                            "text": self._prompt.instructions_template.replace(
                                "{type_name}", type_name
                            ),
                        },
                    ],
                }
            ],
        )

        for block in response["content"]:
            if block["type"] == "tool_use" and block["name"] == _PROPOSE_TOOL_NAME:
                return ProposedOcrConfig(
                    extraction_prompt=block["input"]["extraction_prompt"],
                    extraction_schema=block["input"]["extraction_schema"],
                )
        msg = "Claude did not return the expected config proposal tool call"
        raise RuntimeError(msg)
