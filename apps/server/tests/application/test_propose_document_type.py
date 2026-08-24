"""Proposing a configuration without committing to it."""

import pytest

from server.application.use_cases import ProposeDocumentType, ProposeDocumentTypeInput
from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    FieldRole,
    ProposedField,
    ProposedOcrConfig,
)

SAMPLE = DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="cert.pdf")


class _Configurator:
    def __init__(self, proposal: ProposedOcrConfig) -> None:
        self._proposal = proposal
        self.calls = 0
        self.guidance = ""
        self.base = None

    def propose_config(self, content, type_name, concepts=(), guidance="", base=None):
        self.calls += 1
        self.guidance = guidance
        self.base = base
        return self._proposal


class _Repository:
    def __init__(self, document_type=None) -> None:
        self.saved = []
        self._document_type = document_type

    def save(self, document_type) -> None:
        self.saved.append(document_type)

    def get(self, document_type_id):
        return self._document_type


def test_a_proposal_is_returned_and_nothing_is_stored():
    """Saving the AI's twenty fields made pruning the accountant's problem
    afterwards; this makes choosing their decision up front."""
    configurator = _Configurator(
        ProposedOcrConfig(
            extraction_prompt="Extract it.",
            extraction_schema={"type": "object"},
            fields=(
                ProposedField("nit", "NIT del fondo", FieldRole.IDENTIFIER, "800.170.494"),
                ProposedField("aportes", "Aportes consignados", FieldRole.AMOUNT, "10.499.895"),
                ProposedField("ciudad", "Ciudad", FieldRole.CONTEXT, "Medellín"),
            ),
        )
    )

    proposal = ProposeDocumentType(configurator, _Repository()).execute(
        ProposeDocumentTypeInput(
            type_name="Certificado Protección",
            sample_document=SAMPLE,
            concepts=(ConceptOption("bank:x", "X"),),
        )
    )

    assert configurator.calls == 1
    assert [f.role for f in proposal.fields] == [
        FieldRole.IDENTIFIER,
        FieldRole.AMOUNT,
        FieldRole.CONTEXT,
    ]
    # The sample value travels so a field is recognisable without the document
    # open beside the screen.
    assert proposal.fields[0].sample_value == "800.170.494"


def _configurator() -> _Configurator:
    return _Configurator(
        ProposedOcrConfig(extraction_prompt="Extract it.", extraction_schema={"type": "object"})
    )


def test_a_first_reading_revises_nothing():
    configurator = _configurator()

    ProposeDocumentType(configurator, _Repository()).execute(
        ProposeDocumentTypeInput(type_name="Certificado", sample_document=SAMPLE)
    )

    assert configurator.base is None
    assert configurator.guidance == ""


def test_naming_a_type_makes_it_a_revision_of_what_is_stored():
    """The mappings are keyed by path, so a regeneration has to start from the
    schema that already exists rather than invent a second one beside it."""
    from datetime import UTC, datetime

    from server.domain.entities import DocumentType

    stored = DocumentType(
        id="type-1",
        name="Certificado",
        description="",
        extraction_prompt="Read the obligations table.",
        extraction_schema={"type": "object", "properties": {"capital": {"type": "number"}}},
        active=True,
        created_at=datetime.now(UTC),
    )
    configurator = _configurator()

    ProposeDocumentType(configurator, _Repository(stored)).execute(
        ProposeDocumentTypeInput(
            type_name="Certificado",
            sample_document=SAMPLE,
            document_type_id="type-1",
            guidance="La tabla tiene una fila por obligación.",
        )
    )

    assert configurator.base.extraction_prompt == "Read the obligations table."
    assert configurator.base.extraction_schema == stored.extraction_schema
    assert configurator.guidance == "La tabla tiene una fila por obligación."


def test_revising_a_type_that_is_gone_is_refused_before_the_vision_call():
    from server.application.use_cases.update_document_type import DocumentTypeNotFound

    configurator = _configurator()

    with pytest.raises(DocumentTypeNotFound):
        ProposeDocumentType(configurator, _Repository()).execute(
            ProposeDocumentTypeInput(
                type_name="Certificado", sample_document=SAMPLE, document_type_id="gone"
            )
        )
    assert configurator.calls == 0
