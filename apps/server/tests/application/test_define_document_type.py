"""Defining a document type, including how its fields map onto concepts."""

import pytest

from server.application.use_cases import DefineDocumentType, DefineDocumentTypeInput
from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    ProposedFieldMapping,
    ProposedOcrConfig,
)
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentTypeRepository,
)

SAMPLE = DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="cert.pdf")

CONCEPTS = (
    ConceptOption(id="bank:cert_saldo_cuentas_ahorro", label="Saldo de ahorros"),
    ConceptOption(id="bank:cert_gmf_valor", label="GMF retenido"),
)


class _Configurator:
    def __init__(self, proposal: ProposedOcrConfig) -> None:
        self._proposal = proposal
        self.seen_concepts: tuple[ConceptOption, ...] | None = None
        self.seen_name: str | None = None

    def propose_config(self, content, type_name, concepts=()):
        self.seen_concepts = tuple(concepts)
        self.seen_name = type_name
        return self._proposal


def _proposal(**kwargs) -> ProposedOcrConfig:
    return ProposedOcrConfig(
        extraction_prompt="Extract the balances.",
        extraction_schema={"type": "object", "properties": {"saldo": {"type": "string"}}},
        **kwargs,
    )


def _run(proposal, concepts=CONCEPTS):
    types = InMemoryDocumentTypeRepository()
    configurator = _Configurator(proposal)
    result = DefineDocumentType(configurator, types).execute(
        DefineDocumentTypeInput(
            name="Certificado Bancolombia",
            description="Certificado anual",
            sample_document=SAMPLE,
            concepts=concepts,
        )
    )
    return result, types, configurator


def test_the_vocabulary_is_handed_to_the_ai():
    """The mapping is proposed in the same call that invents the field names —
    the only moment the model can tie the two together reliably."""
    _, _, configurator = _run(_proposal())
    assert configurator.seen_concepts == CONCEPTS
    assert configurator.seen_name == "Certificado Bancolombia"


def test_the_proposed_type_is_saved_and_returned_with_its_mapping():
    mappings = (
        ProposedFieldMapping(field_path="saldo", concept_id="bank:cert_saldo_cuentas_ahorro"),
        ProposedFieldMapping(
            field_path="cargo", concept_id="bank:cert_gmf_valor", sign=-1, account_path="cuenta"
        ),
    )
    result, types, _ = _run(_proposal(field_mappings=mappings))

    saved = types.list_active()
    assert len(saved) == 1
    assert result.document_type.id == saved[0].id
    assert result.document_type.extraction_prompt == "Extract the balances."
    assert result.field_mappings == mappings
    assert result.field_mappings[1].sign == -1
    assert result.field_mappings[1].account_path == "cuenta"


def test_fields_the_ai_left_unmapped_are_reported_not_dropped():
    """They still get extracted; they just cannot be reconciled. Surfacing them
    makes that a visible decision rather than a silent omission."""
    result, _, _ = _run(
        _proposal(unmapped_fields=(("fecha_expedicion", "not a monetary concept"),))
    )
    assert result.unmapped_fields == (("fecha_expedicion", "not a monetary concept"),)
    assert result.field_mappings == ()


def test_a_type_can_be_defined_with_no_vocabulary_at_all():
    """Extraction without reconciliation behind it stays possible."""
    _, types, configurator = _run(_proposal(), concepts=())
    assert configurator.seen_concepts == ()
    assert len(types.list_active()) == 1


def test_an_approved_configuration_is_saved_without_asking_the_ai_again():
    """Two runs of the model over one document do not agree field for field,
    so re-proposing here would store something other than what was reviewed —
    and charge for a second run to do it."""
    types = InMemoryDocumentTypeRepository()
    configurator = _Configurator(_proposal())

    result = DefineDocumentType(configurator, types).execute(
        DefineDocumentTypeInput(
            name="Certificado Protección",
            description="Aportes y retenciones",
            extraction_prompt="Extract the approved fields.",
            extraction_schema={"type": "object", "properties": {"nit": {"type": "string"}}},
            field_mappings=(ProposedFieldMapping("aportes", "bank:cert_cesantias_abonadas"),),
            reporter_path="nit",
        )
    )

    assert configurator.seen_name is None
    assert result.document_type.extraction_prompt == "Extract the approved fields."
    assert result.document_type.extraction_schema["properties"] == {"nit": {"type": "string"}}
    assert result.field_mappings[0].concept_id == "bank:cert_cesantias_abonadas"
    assert result.reporter_path == "nit"


def test_without_an_approved_configuration_it_still_proposes_one():
    _, _, configurator = _run(_proposal())
    assert configurator.seen_name == "Certificado Bancolombia"


def test_defining_with_neither_a_configuration_nor_a_sample_is_refused():
    with pytest.raises(ValueError, match="approved configuration"):
        DefineDocumentType(_Configurator(_proposal()), InMemoryDocumentTypeRepository()).execute(
            DefineDocumentTypeInput(name="X", description="d")
        )
