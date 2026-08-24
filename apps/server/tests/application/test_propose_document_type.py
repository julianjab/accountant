"""Proposing a configuration without committing to it."""

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

    def propose_config(self, content, type_name, concepts=()):
        self.calls += 1
        return self._proposal


class _Repository:
    def __init__(self) -> None:
        self.saved = []

    def save(self, document_type) -> None:
        self.saved.append(document_type)


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

    proposal = ProposeDocumentType(configurator).execute(
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
