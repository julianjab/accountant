"""Editing a document type after the AI proposed it.

The AI proposal is a starting point: it routinely extracts more fields than the
accountant needs, and the only way to trim it used to be defining the type all
over again from a fresh sample.
"""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    DocumentTypeNotFound,
    UpdateDocumentType,
    UpdateDocumentTypeInput,
)
from server.domain.entities import DocumentType
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentTypeRepository,
)

SCHEMA = {
    "type": "object",
    "properties": {"saldo": {"type": "string"}, "gmf": {"type": "string"}},
}


def _stored() -> InMemoryDocumentTypeRepository:
    types = InMemoryDocumentTypeRepository()
    types.save(
        DocumentType(
            id="type-1",
            name="Certificado Bancolombia",
            description="Certificado anual",
            extraction_prompt="Extract the balances.",
            extraction_schema=SCHEMA,
            active=True,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
    )
    return types


def test_the_schema_can_be_trimmed_to_the_fields_that_matter():
    types = _stored()
    trimmed = {"type": "object", "properties": {"saldo": {"type": "string"}}}

    updated = UpdateDocumentType(types).execute(
        UpdateDocumentTypeInput(document_type_id="type-1", extraction_schema=trimmed)
    )

    assert updated.extraction_schema == trimmed
    assert types.get("type-1").extraction_schema == trimmed


def test_fields_left_out_of_the_edit_keep_their_stored_value():
    """The usual edit touches one field, and a client that had to resend the
    whole type would overwrite with whatever it had read before."""
    types = _stored()

    updated = UpdateDocumentType(types).execute(
        UpdateDocumentTypeInput(document_type_id="type-1", name="Certificado 2025")
    )

    assert updated.name == "Certificado 2025"
    assert updated.description == "Certificado anual"
    assert updated.extraction_prompt == "Extract the balances."
    assert updated.extraction_schema == SCHEMA
    assert updated.active is True


def test_a_type_can_be_deactivated_without_losing_its_configuration():
    """Deactivating is how a type stops being classified against; the prompt
    and schema stay so it can be turned back on without a new AI pass."""
    types = _stored()

    updated = UpdateDocumentType(types).execute(
        UpdateDocumentTypeInput(document_type_id="type-1", active=False)
    )

    assert updated.active is False
    assert updated.extraction_schema == SCHEMA


def test_the_identity_of_the_type_survives_an_edit():
    """Editing must not fork the type: documents already extracted reference it
    by id, and a new id would orphan every one of them."""
    types = _stored()
    created_at = types.get("type-1").created_at

    updated = UpdateDocumentType(types).execute(
        UpdateDocumentTypeInput(document_type_id="type-1", description="Certificado 2025")
    )

    assert updated.id == "type-1"
    assert updated.created_at == created_at
    assert len(types.list_all()) == 1


def test_editing_a_type_that_does_not_exist_is_refused():
    """Saving it anyway would create a type with no prompt and no schema, which
    classification would then offer as a candidate."""
    types = _stored()

    with pytest.raises(DocumentTypeNotFound):
        UpdateDocumentType(types).execute(UpdateDocumentTypeInput(document_type_id="ghost"))
