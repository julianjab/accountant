"""The Claude adapter that proposes an extraction config, and now a mapping."""

import pytest

from server.domain.ports import ConceptOption, DocumentContent
from server.infrastructure.adapters.claude_document_type_configurator import (
    ClaudeDocumentTypeConfigurator,
)
from server.infrastructure.config.prompts import TemplatedPrompt

SAMPLE = DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="cert.pdf")

PROMPT = TemplatedPrompt(
    system="You design extraction configs.",
    instructions_template='Sample "{type_name}".{mapping_instructions}',
)

CONCEPTS = (
    ConceptOption(id="bank:cert_saldo_cuentas_ahorro", label="Saldo", description="El saldo"),
    ConceptOption(id="bank:cert_gmf_valor", label="GMF"),
)


class _Provider:
    def __init__(self, tool_input: dict) -> None:
        self._tool_input = tool_input
        self.request: dict | None = None

    def create_message(self, **kwargs):
        self.request = kwargs
        return {
            "content": [
                {"type": "tool_use", "name": "propose_ocr_config", "input": self._tool_input}
            ]
        }


def _configure(tool_input, concepts=CONCEPTS):
    provider = _Provider(tool_input)
    adapter = ClaudeDocumentTypeConfigurator(provider, "claude-x", PROMPT)
    return adapter.propose_config(SAMPLE, "Certificado", concepts), provider


def test_the_concept_ids_are_an_enum_so_none_can_be_invented():
    """A hallucinated id would be stored, produce facts no rule selects, and
    leave the claim it was meant to satisfy reported as missing."""
    _, provider = _configure({"extraction_prompt": "p", "extraction_schema": {}})
    schema = provider.request["tools"][0]["input_schema"]["properties"]
    concept_field = schema["field_mappings"]["items"]["properties"]["concept_id"]
    assert concept_field["enum"] == ["bank:cert_saldo_cuentas_ahorro", "bank:cert_gmf_valor"]


def test_the_catalog_reaches_the_instructions():
    _, provider = _configure({"extraction_prompt": "p", "extraction_schema": {}})
    text = provider.request["messages"][0]["content"][-1]["text"]
    assert "bank:cert_saldo_cuentas_ahorro: Saldo — El saldo" in text
    assert "bank:cert_gmf_valor: GMF" in text


def test_no_vocabulary_means_no_mapping_asked_for():
    _, provider = _configure({"extraction_prompt": "p", "extraction_schema": {}}, concepts=())
    schema = provider.request["tools"][0]["input_schema"]["properties"]
    assert "field_mappings" not in schema
    text = provider.request["messages"][0]["content"][-1]["text"]
    assert "{mapping_instructions}" not in text


def test_the_proposed_mapping_is_read_back():
    proposal, _ = _configure(
        {
            "extraction_prompt": "Extract it.",
            "extraction_schema": {"type": "object"},
            "field_mappings": [
                {
                    "field_path": "cuentas[].saldo",
                    "concept_id": "bank:cert_saldo_cuentas_ahorro",
                    "account_path": "cuentas[].numero",
                },
                {"field_path": "gmf", "concept_id": "bank:cert_gmf_valor", "sign": -1},
            ],
            "unmapped_fields": [{"field_path": "fecha", "reason": "not monetary"}],
        }
    )
    assert proposal.extraction_prompt == "Extract it."
    assert proposal.field_mappings[0].account_path == "cuentas[].numero"
    assert proposal.field_mappings[0].sign == 1
    assert proposal.field_mappings[1].sign == -1
    assert proposal.unmapped_fields == (("fecha", "not monetary"),)


def test_a_response_without_the_tool_call_is_an_error():
    provider = _Provider({})
    provider.create_message = lambda **kwargs: {"content": [{"type": "text", "text": "hi"}]}
    adapter = ClaudeDocumentTypeConfigurator(provider, "claude-x", PROMPT)
    try:
        adapter.propose_config(SAMPLE, "Certificado", CONCEPTS)
    except RuntimeError as error:
        assert "proposal tool call" in str(error)
    else:
        raise AssertionError("expected a RuntimeError")


def test_a_concept_the_model_invented_is_reported_instead_of_stored():
    """The enum steers the model; it does not bind it. An invented id would
    reach storage and then select nothing, leaving the claim it was meant to
    satisfy reported as missing with nothing pointing at the mapping."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {},
            "field_mappings": [
                {"field_path": "saldo", "concept_id": "bank:invented"},
                {"field_path": "gmf", "concept_id": "bank:cert_gmf_valor"},
            ],
        }
    )
    assert [m.concept_id for m in proposal.field_mappings] == ["bank:cert_gmf_valor"]
    assert proposal.unmapped_fields == (("saldo", "proposed an unknown concept (bank:invented)"),)


def test_an_invalid_sign_is_reported_instead_of_stored():
    """A sign of 0 would silently zero every amount the field contributes and a
    2 would double it, with nothing downstream to notice."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {},
            "field_mappings": [
                {"field_path": "saldo", "concept_id": "bank:cert_gmf_valor", "sign": 0},
                {"field_path": "otro", "concept_id": "bank:cert_gmf_valor", "sign": 2},
            ],
        }
    )
    assert proposal.field_mappings == ()
    assert [reason for _, reason in proposal.unmapped_fields] == [
        "proposed an invalid sign (0)",
        "proposed an invalid sign (2)",
    ]


def test_a_bad_entry_does_not_discard_the_whole_proposal():
    """The document type itself is fine; failing the request would leave it
    saved with no mapping at all."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "Extract it.",
            "extraction_schema": {"type": "object"},
            "field_mappings": [{"field_path": "x", "concept_id": "nope"}],
        }
    )
    assert proposal.extraction_prompt == "Extract it."
    assert proposal.extraction_schema == {"type": "object"}


def test_a_field_the_schema_never_declared_is_reported_instead_of_stored():
    """Same silent failure as an invented concept: the type looks mapped, the
    projection finds nothing, and the claim stays reported as missing."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {
                "type": "object",
                "properties": {
                    "saldo": {"type": "string"},
                    "cuentas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"numero": {"type": "string"}},
                        },
                    },
                },
            },
            "field_mappings": [
                {"field_path": "saldo", "concept_id": "bank:cert_gmf_valor"},
                {"field_path": "inventado", "concept_id": "bank:cert_gmf_valor"},
                {"field_path": "cuentas[].numero", "concept_id": "bank:cert_gmf_valor"},
                {"field_path": "cuentas[].ausente", "concept_id": "bank:cert_gmf_valor"},
                {"field_path": "saldo[]", "concept_id": "bank:cert_gmf_valor"},
            ],
        }
    )
    assert [m.field_path for m in proposal.field_mappings] == ["saldo", "cuentas[].numero"]
    assert [path for path, _ in proposal.unmapped_fields] == [
        "inventado",
        "cuentas[].ausente",
        "saldo[]",
    ]


def test_an_account_path_the_schema_lacks_is_dropped_but_the_amount_still_maps():
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {"type": "object", "properties": {"saldo": {"type": "string"}}},
            "field_mappings": [
                {
                    "field_path": "saldo",
                    "concept_id": "bank:cert_gmf_valor",
                    "account_path": "no_existe",
                }
            ],
        }
    )
    assert len(proposal.field_mappings) == 1
    assert proposal.field_mappings[0].account_path is None


@pytest.mark.parametrize(
    "entry",
    [
        {"concept_id": "bank:cert_gmf_valor"},
        {"field_path": "", "concept_id": "bank:cert_gmf_valor"},
        {"field_path": 7, "concept_id": "bank:cert_gmf_valor"},
        "not an object",
    ],
)
def test_a_malformed_entry_does_not_crash_the_request(entry):
    """`required` in the tool schema is advisory too. Indexing it directly
    raised after the document type had already been saved."""
    proposal, _ = _configure(
        {"extraction_prompt": "p", "extraction_schema": {}, "field_mappings": [entry]}
    )
    assert proposal.field_mappings == ()
    assert len(proposal.unmapped_fields) == 1


@pytest.mark.parametrize("value", [None, [], "nope"])
def test_a_null_or_odd_mappings_field_is_treated_as_none_proposed(value):
    """`.get(key, [])` returns None when the key is present and null, so the
    default never fires."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {},
            "field_mappings": value,
            "unmapped_fields": value,
        }
    )
    assert proposal.field_mappings == ()
    assert proposal.unmapped_fields == ()


def test_malformed_unmapped_entries_are_skipped_rather_than_raising():
    """This runs after the AI call is paid for and before the type is saved."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {},
            "unmapped_fields": [
                "just a string",
                {"reason": "no field path"},
                {"field_path": 7, "reason": "not a string"},
                {"field_path": "fecha"},
                {"field_path": "sello", "reason": "not monetary"},
            ],
        }
    )
    assert proposal.unmapped_fields == (("fecha", ""), ("sello", "not monetary"))


def test_the_reporting_party_is_required_whenever_a_vocabulary_is_offered():
    """The mappings are worthless without it, so an omitted path would throw
    away every mapping the model just produced."""
    _, provider = _configure({"extraction_prompt": "p", "extraction_schema": {}})
    assert provider.request["tools"][0]["input_schema"]["required"] == [
        "extraction_prompt",
        "extraction_schema",
        "fields",
        "reporter_path",
    ]
    text = provider.request["messages"][0]["content"][-1]["text"]
    assert "reporter_path" in text


def test_no_vocabulary_means_the_reporting_party_is_not_demanded():
    _, provider = _configure({"extraction_prompt": "p", "extraction_schema": {}}, concepts=())
    assert provider.request["tools"][0]["input_schema"]["required"] == [
        "extraction_prompt",
        "extraction_schema",
        "fields",
    ]


def test_the_document_level_paths_are_read_back():
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {
                "type": "object",
                "properties": {
                    "nit": {"type": "string"},
                    "emisor": {"type": "string"},
                    "anio": {"type": "string"},
                },
            },
            "reporter_path": "nit",
            "reporter_name_path": "emisor",
            "period_path": "anio",
        }
    )
    assert proposal.reporter_path == "nit"
    assert proposal.reporter_name_path == "emisor"
    assert proposal.period_path == "anio"


def test_a_document_level_path_the_schema_lacks_says_what_actually_went_wrong():
    """Nulling it silently surfaces later as "the document does not say who
    reports these amounts", which sends the reader looking in the wrong place."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {"type": "object", "properties": {"nit": {"type": "string"}}},
            "reporter_path": "emisor.nit",
        }
    )
    assert proposal.reporter_path is None
    assert proposal.unmapped_fields == (
        ("emisor.nit", "proposed as reporter_path but the schema does not declare it"),
    )


def test_each_proposed_field_says_what_it_is():
    """So a screen can offer the identifier and the figures already ticked,
    instead of twenty rows to triage."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {},
            "fields": [
                {
                    "path": "nit",
                    "label": "NIT",
                    "role": "identifier",
                    "sample_value": "800170494",
                    "section": "Datos del agente retenedor",
                },
                {"path": "total", "label": "Total", "role": "amount", "sample_value": "10499895"},
                {"path": "ciudad", "label": "Ciudad", "role": "context"},
            ],
        }
    )
    assert [(f.path, f.role.value) for f in proposal.fields] == [
        ("nit", "identifier"),
        ("total", "amount"),
        ("ciudad", "context"),
    ]
    assert proposal.fields[2].sample_value == ""
    # Sections let a selection screen be laid out the way the paper is.
    assert proposal.fields[0].section == "Datos del agente retenedor"
    assert proposal.fields[2].section == ""


def test_a_field_with_an_unknown_role_is_still_offered():
    """Losing its head start in the selection beats disappearing."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "p",
            "extraction_schema": {},
            "fields": [
                {"path": "raro", "label": "Raro", "role": "inventado"},
                {"label": "sin ruta", "role": "amount"},
                "no es un objeto",
            ],
        }
    )
    assert [(f.path, f.role.value) for f in proposal.fields] == [("raro", "context")]


def test_the_field_descriptions_are_demanded_rather_than_hoped_for():
    """Left optional the model simply omitted them, and the screen fell back to
    listing the schema's own leaves: every field unnamed, unsectioned, with no
    sample value and classified as context."""
    _, provider = _configure({"extraction_prompt": "p", "extraction_schema": {}})

    schema = provider.request["tools"][0]["input_schema"]
    assert "fields" in schema["required"]
    assert schema["properties"]["fields"]["items"]["required"] == [
        "path",
        "label",
        "role",
        "sample_value",
        "section",
    ]


def test_a_schema_that_arrives_as_json_text_is_still_a_schema():
    """The schema is the one tool argument whose value is itself JSON, and the
    model returns it as a string often enough that a 500 here means a paid-for
    vision call thrown away over a `json.loads`."""
    proposal, _ = _configure(
        {
            "extraction_prompt": "Extract it.",
            "extraction_schema": '{"type": "object", "properties": {"gmf": {"type": "number"}}}',
            "field_mappings": [{"field_path": "gmf", "concept_id": "bank:cert_gmf_valor"}],
        }
    )
    assert proposal.extraction_schema == {
        "type": "object",
        "properties": {"gmf": {"type": "number"}},
    }
    # Read as an object, the paths it declares resolve — so the mapping the
    # model proposed against it survives instead of being rejected.
    assert [m.field_path for m in proposal.field_mappings] == ["gmf"]


@pytest.mark.parametrize("value", [None, "not json at all", ["type", "object"], 7])
def test_a_schema_that_is_not_an_object_fails_loudly(value):
    """Every field path is a path into this schema; without one there is
    nothing to extract, so this is the part worth refusing over."""
    with pytest.raises(RuntimeError, match="not a JSON object"):
        _configure({"extraction_prompt": "p", "extraction_schema": value})
