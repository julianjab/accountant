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
                payload = block["input"]
                schema = payload.get("extraction_schema")
                mappings, rejected = _read_mappings(payload, concepts, schema)
                return ProposedOcrConfig(
                    extraction_prompt=payload["extraction_prompt"],
                    extraction_schema=payload["extraction_schema"],
                    field_mappings=mappings,
                    unmapped_fields=(*_read_unmapped(payload), *rejected),
                    reporter_path=_read_path(payload, "reporter_path", schema),
                    reporter_name_path=_read_path(payload, "reporter_name_path", schema),
                    period_path=_read_path(payload, "period_path", schema),
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
        "reporter_path": {
            "type": "string",
            "description": "Path to the identifier of the party issuing this document — "
            "the bank or employer whose figures these are. Required for any of the "
            "mappings to be usable: an amount that cannot be attributed to a reporting "
            "party cannot be checked against what that party declared elsewhere.",
        },
        "reporter_name_path": {
            "type": "string",
            "description": "Path to that party's name, for display.",
        },
        "period_path": {
            "type": "string",
            "description": "Path to the tax year or period the document covers, so a "
            "certificate for one year is not reconciled against another.",
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
    payload: dict, concepts: Sequence[ConceptOption], schema: object
) -> tuple[tuple[ProposedFieldMapping, ...], tuple[tuple[str, str], ...]]:
    """Reads the mappings, setting aside every entry that cannot be trusted.

    The tool schema steers the model; it does not bind it. Its `enum` and its
    `required` are both advisory, so an entry can arrive with an invented
    concept, a sign that is neither +1 nor -1, a field the proposed schema
    never declared, or a missing key altogether.

    Every one of those fails the same silent way: the mapping is stored, the
    document type looks configured, the projection produces no fact, and the
    claim it was meant to satisfy stays reported as missing with nothing
    pointing back here. So each is set aside with a reason rather than stored —
    and rather than raised, because the document type itself is fine and
    failing the request would leave it saved with no mapping at all.
    """
    known = {c.id for c in concepts}
    mappings: list[ProposedFieldMapping] = []
    rejected: list[tuple[str, str]] = []

    for entry in _entries(payload, "field_mappings"):
        if not isinstance(entry, dict):
            rejected.append(("?", f"proposed a mapping that is not an object ({entry!r})"))
            continue
        field_path = entry.get("field_path")
        concept_id = entry.get("concept_id")
        sign = entry.get("sign", 1)
        if not isinstance(field_path, str) or not field_path:
            rejected.append(("?", "proposed a mapping with no field path"))
            continue
        if concept_id not in known:
            rejected.append((field_path, f"proposed an unknown concept ({concept_id})"))
            continue
        if sign not in (1, -1):
            rejected.append((field_path, f"proposed an invalid sign ({sign})"))
            continue
        if not _resolves_in(field_path, schema):
            rejected.append((field_path, "proposed a field the schema does not declare"))
            continue
        account_path = entry.get("account_path") or None
        if account_path is not None and not _resolves_in(account_path, schema):
            # The amount still maps; it just cannot be tied to an account.
            account_path = None
        mappings.append(
            ProposedFieldMapping(
                field_path=field_path,
                concept_id=concept_id,
                account_path=account_path,
                sign=sign,
            )
        )
    return tuple(mappings), tuple(rejected)


def _resolves_in(path: str, schema: object) -> bool:
    """Whether a dotted path points at something the proposed schema declares.

    Walks `properties`, and `items` for a `[]` segment. A schema that declares
    no properties cannot be checked against, so the path is accepted there:
    rejecting every mapping would be worse than the gap this closes.
    """
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        return True
    node: object = schema
    for segment in path.split("."):
        iterate = segment.endswith("[]")
        key = segment[:-2] if iterate else segment
        properties = node.get("properties") if isinstance(node, dict) else None
        if not isinstance(properties, dict) or key not in properties:
            return False
        node = properties[key]
        if iterate:
            if not isinstance(node, dict) or node.get("type") != "array":
                return False
            node = node.get("items", {})
    return True


def _read_unmapped(payload: dict) -> tuple[tuple[str, str], ...]:
    """Reads what the model said it could not map, guarding it the same way.

    The premise `_read_mappings` is built on — the tool schema steers the model
    without binding it — applies here too. An entry arriving as a bare string,
    or without a field path, would raise after the AI call had already been
    paid for and before the document type was ever saved.
    """
    return tuple(
        (entry["field_path"], str(entry.get("reason", "")))
        for entry in _entries(payload, "unmapped_fields")
        if isinstance(entry, dict) and isinstance(entry.get("field_path"), str)
    )


def _entries(payload: dict, key: str) -> list:
    """The list at `key`, or nothing when the model sent something else.

    A default on .get does not cover a key present with a null value, and a
    bare string would otherwise be iterated one character at a time.
    """
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _read_path(payload: dict, key: str, schema: object) -> str | None:
    """A single path from the proposal, dropped unless the schema declares it."""
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        return None
    return value if _resolves_in(value, schema) else None
