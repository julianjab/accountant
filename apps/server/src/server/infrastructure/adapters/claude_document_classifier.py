import base64

from server.domain.entities import DocumentType
from server.domain.ports import DocumentContent
from server.infrastructure.config.prompts import TemplatedPrompt
from server.infrastructure.providers.ai_provider import AIProvider

_CLASSIFY_TOOL_NAME = "pick_document_type"


class ClaudeDocumentClassifier:
    """DocumentClassifier adapter: a cheap/fast Claude call picks the matching
    document type among the ones configured, or none if there is no match."""

    def __init__(self, provider: AIProvider, model: str, prompt: TemplatedPrompt) -> None:
        self._provider = provider
        self._model = model
        self._prompt = prompt

    def classify(
        self, content: DocumentContent, available_types: list[DocumentType]
    ) -> DocumentType | None:
        if not available_types:
            return None

        by_id = {t.id: t for t in available_types}
        response = self._provider.create_message(
            model=self._model,
            system=self._prompt.system,
            max_tokens=256,
            tools=[
                {
                    "name": _CLASSIFY_TOOL_NAME,
                    "description": "Report which configured document type matches this document.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "document_type_id": {
                                "type": ["string", "null"],
                                "enum": [*by_id.keys(), None],
                                "description": "Id of the matching type, or null if none matches.",
                            }
                        },
                        "required": ["document_type_id"],
                    },
                }
            ],
            tool_choice={"type": "tool", "name": _CLASSIFY_TOOL_NAME},
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
                            "text": _build_instructions(self._prompt, available_types),
                        },
                    ],
                }
            ],
        )

        for block in response["content"]:
            if block["type"] == "tool_use" and block["name"] == _CLASSIFY_TOOL_NAME:
                document_type_id = block["input"].get("document_type_id")
                return by_id.get(document_type_id) if document_type_id else None
        return None


def _build_instructions(prompt: TemplatedPrompt, available_types: list[DocumentType]) -> str:
    options = "\n".join(f"- {t.id}: {t.name} — {t.description}" for t in available_types)
    return prompt.instructions_template.replace("{options}", options)
