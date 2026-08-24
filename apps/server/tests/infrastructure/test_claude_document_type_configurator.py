"""The Claude adapter that proposes an extraction config, and now a mapping."""

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
