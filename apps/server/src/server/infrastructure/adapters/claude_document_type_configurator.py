import base64
from collections.abc import Sequence

from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    FieldRole,
    ProposedField,
    ProposedFieldMapping,
    ProposedOcrConfig,
)
from server.infrastructure.config.prompts import TemplatedPrompt
from server.infrastructure.providers.ai_provider import AIProvider
from server.reconciliation.core.projection import path_resolves_in

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
                            "fields": {
                                "type": "array",
                                "description": "Every field the schema declares, so a "
                                "person can be shown the few that matter instead of "
                                "triaging twenty. Most of a certificate is context.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Dotted path, `foo[].bar` for a list.",
                                        },
                                        "label": {
                                            "type": "string",
                                            "description": "How the document itself "
                                            "names this value, in its own language.",
                                        },
                                        "role": {
                                            "type": "string",
                                            "enum": ["identifier", "amount", "context"],
                                            "description": "identifier for a tax, "
                                            "account or document number; amount for a "
                                            "monetary figure; context for dates, "
                                            "names, addresses and notices.",
                                        },
                                        "sample_value": {
                                            "type": "string",
                                            "description": "The value as it reads in "
                                            "this sample, so the field is "
                                            "recognisable without the document open.",
                                        },
                                    },
                                    "required": ["path", "label", "role"],
                                },
                            },
                            **_mapping_properties(concepts),
                        },
                        "required": _required_fields(concepts),
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
                paths, path_problems = _read_paths(payload, schema)
                rejected = (*rejected, *path_problems)
                return ProposedOcrConfig(
                    extraction_prompt=payload["extraction_prompt"],
                    extraction_schema=payload["extraction_schema"],
                    field_mappings=mappings,
                    unmapped_fields=(*_read_unmapped(payload), *rejected),
                    fields=_read_fields(payload),
                    reporter_path=paths["reporter_path"],
                    reporter_name_path=paths["reporter_name_path"],
                    period_path=paths["period_path"],
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
            "description": "Path to the NIT or tax identification NUMBER of the party "
            "issuing this document — never its name. A name cannot be matched against "
            "what other documents report, so a field holding one makes every mapping "
            "below unusable. If the document states both, this must point at the digits.",
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
        "\n\nAlso give reporter_path: the field holding the issuing party's NIT "
        "or tax identification number — the digits, never the name. Amounts are "
        "matched to what a party declared elsewhere by that number, so pointing "
        "this at a name makes every mapping below unusable."
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
        if not path_resolves_in(field_path, schema):
            rejected.append((field_path, "proposed a field the schema does not declare"))
            continue
        account_path = entry.get("account_path") or None
        if account_path is not None and not path_resolves_in(account_path, schema):
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


def _required_fields(concepts: Sequence[ConceptOption]) -> list[str]:
    """What the model must return.

    reporter_path joins the list whenever a vocabulary is offered, because the
    mappings are worthless without it: a fact that cannot be attributed to a
    reporting party is discarded, so an omitted path throws away every mapping
    the model just produced.
    """
    required = ["extraction_prompt", "extraction_schema"]
    if concepts:
        required.append("reporter_path")
    return required


def _read_paths(
    payload: dict, schema: object
) -> tuple[dict[str, str | None], tuple[tuple[str, str], ...]]:
    """The document-level paths, with a reason for any that had to be dropped.

    A path the model's own schema does not declare is reported rather than
    quietly nulled: dropping it silently would surface later as "the document
    does not say who reports these amounts", which is not what went wrong and
    sends whoever reads it looking in the wrong place.
    """
    paths: dict[str, str | None] = {}
    problems: list[tuple[str, str]] = []
    for key in ("reporter_path", "reporter_name_path", "period_path"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            paths[key] = None
            continue
        if not path_resolves_in(value, schema):
            problems.append((value, f"proposed as {key} but the schema does not declare it"))
            paths[key] = None
            continue
        paths[key] = value
    return paths, tuple(problems)


def _read_fields(payload: dict) -> tuple[ProposedField, ...]:
    """Reads the field inventory, skipping anything malformed.

    Guarded like every other part of the response: this arrives after the AI
    call is paid for, and one odd entry must not cost the whole proposal.
    """
    fields: list[ProposedField] = []
    for entry in _entries(payload, "fields"):
        if not isinstance(entry, dict):
            continue
        path, label = entry.get("path"), entry.get("label")
        if not isinstance(path, str) or not path:
            continue
        try:
            role = FieldRole(entry.get("role"))
        except ValueError:
            # An unrecognised role is not a reason to hide the field; it just
            # loses its head start in the selection.
            role = FieldRole.CONTEXT
        fields.append(
            ProposedField(
                path=path,
                label=label if isinstance(label, str) and label else path,
                role=role,
                sample_value=str(entry.get("sample_value", "")),
            )
        )
    return tuple(fields)
