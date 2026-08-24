import base64
from collections.abc import Sequence

from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    ProposedFieldMapping,
    ProposedOcrConfig,
)
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

    def propose_config(
        self,
        content: DocumentContent,
        type_name: str,
        concepts: Sequence[ConceptOption] = (),
    ) -> ProposedOcrConfig:
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
                            **_mapping_properties(concepts),
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
                            ).replace("{mapping_instructions}", _mapping_instructions(concepts)),
                        },
                    ],
                }
            ],
        )

        for block in response["content"]:
            if block["type"] == "tool_use" and block["name"] == _PROPOSE_TOOL_NAME:
                mappings, rejected = _read_mappings(block["input"], concepts)
                return ProposedOcrConfig(
                    extraction_prompt=block["input"]["extraction_prompt"],
                    extraction_schema=block["input"]["extraction_schema"],
                    field_mappings=mappings,
                    unmapped_fields=(*_read_unmapped(block["input"]), *rejected),
                )
        msg = "Claude did not return the expected config proposal tool call"
        raise RuntimeError(msg)


def _mapping_properties(concepts: Sequence[ConceptOption]) -> dict:
    """The mapping half of the tool schema, added only when a vocabulary exists.

    concept_id is an enum of the ids on offer, so the model cannot invent one.
    Validation downstream then becomes a backstop rather than the only defence:
    a hallucinated id would be stored, produce facts no rule ever selects, and
    leave the claim it was meant to satisfy reported as missing with nothing
    pointing back at the mapping.
    """
    if not concepts:
        return {}
    return {
        "field_mappings": {
            "type": "array",
            "description": "One entry per extracted field that corresponds to a concept.",
            "items": {
                "type": "object",
                "properties": {
                    "field_path": {
                        "type": "string",
                        "description": "Dotted path into the extraction schema, e.g. "
                        "`balance` or `accounts[].balance` to walk a list.",
                    },
                    "concept_id": {
                        "type": "string",
                        "enum": [c.id for c in concepts],
                    },
                    "account_path": {
                        "type": "string",
                        "description": "Path to the account identifier this amount belongs "
                        "to, when the document states one.",
                    },
                    "sign": {
                        "type": "integer",
                        "enum": [1, -1],
                        "description": "-1 when the document states the figure with the "
                        "opposite sign to the concept.",
                    },
                },
                "required": ["field_path", "concept_id"],
            },
        },
        "unmapped_fields": {
            "type": "array",
            "description": "Fields worth extracting that no concept covers, with the "
            "reason. Report them rather than forcing an approximate match.",
            "items": {
                "type": "object",
                "properties": {
                    "field_path": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["field_path", "reason"],
            },
        },
    }


def _mapping_instructions(concepts: Sequence[ConceptOption]) -> str:
    if not concepts:
        return ""
    catalog = "\n".join(
        f"- {c.id}: {c.label}" + (f" — {c.description}" if c.description else "") for c in concepts
    )
    return (
        "\n\nThen map the fields you just defined onto these concepts, so the "
        "amounts can be reconciled against what other documents report:\n"
        f"{catalog}\n"
        "Map a field only when it means the same thing as the concept. A wrong "
        "mapping is worse than none: it makes two unrelated figures reconcile "
        "against each other. List anything you leave out under unmapped_fields "
        "with the reason."
    )


def _read_mappings(
    payload: dict, concepts: Sequence[ConceptOption]
) -> tuple[tuple[ProposedFieldMapping, ...], tuple[tuple[str, str], ...]]:
    """Reads the mappings, setting aside any the model got wrong.

    The enum in the tool schema steers the model; it does not bind it. An
    invented concept id would otherwise reach storage and then select nothing,
    and a sign of 0 would silently zero the field's amounts. Both are reported
    as unmapped rather than raised: the document type itself is fine, and
    failing the request would leave it saved with no mapping at all — the
    half-configured state this is meant to prevent.
    """
    known = {c.id for c in concepts}
    mappings: list[ProposedFieldMapping] = []
    rejected: list[tuple[str, str]] = []
    for entry in payload.get("field_mappings", []):
        field_path, concept_id = entry["field_path"], entry["concept_id"]
        sign = entry.get("sign", 1)
        if concept_id not in known:
            rejected.append((field_path, f"proposed an unknown concept ({concept_id})"))
            continue
        if sign not in (1, -1):
            rejected.append((field_path, f"proposed an invalid sign ({sign})"))
            continue
        mappings.append(
            ProposedFieldMapping(
                field_path=field_path,
                concept_id=concept_id,
                account_path=entry.get("account_path") or None,
                sign=sign,
            )
        )
    return tuple(mappings), tuple(rejected)


def _read_unmapped(payload: dict) -> tuple[tuple[str, str], ...]:
    return tuple(
        (entry["field_path"], entry.get("reason", ""))
        for entry in payload.get("unmapped_fields", [])
    )
