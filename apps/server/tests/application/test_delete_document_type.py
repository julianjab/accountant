"""Deleting a document type — and refusing to when it would erase meaning.

Deleting is for undoing a mistake: a duplicate, a type configured against the
wrong sample. Retiring a type that is in use is what `active` is for, and it
keeps every document already classified under it readable.
"""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    DeleteDocumentType,
    DeleteDocumentTypeInput,
    DocumentTypeInUse,
    DocumentTypeNotFound,
)
from server.domain.entities import Document, DocumentStatus, DocumentType
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
)


def _type(type_id: str = "type-1") -> DocumentType:
    return DocumentType(
        id=type_id,
        name="Certificado",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _document(document_type_id: str | None) -> Document:
    return Document(
        id="doc-1",
        client_id="client-1",
        document_type_id=document_type_id,
        drive_file_id="drive-1",
        file_name="cert.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        error=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _delete(*, stored=(), documents=()):
    types = InMemoryDocumentTypeRepository()
    for document_type in stored:
        types.save(document_type)
    docs = InMemoryDocumentRepository()
    for document in documents:
        docs.save(document)
    return DeleteDocumentType(types, docs), types


def test_a_type_nothing_was_filed_under_is_deleted():
    use_case, types = _delete(stored=[_type()])

    use_case.execute(DeleteDocumentTypeInput(document_type_id="type-1"))

    assert types.get("type-1") is None


def test_a_type_documents_were_classified_as_is_refused():
    """Cascading would leave those documents with an id pointing at nothing:
    the screen could not say what kind of paper each one is, the extracted
    fields would lose the labels that made them legible, and the
    reconciliation the mapping that made their figures comparable."""
    use_case, types = _delete(stored=[_type()], documents=[_document("type-1")])

    with pytest.raises(DocumentTypeInUse) as raised:
        use_case.execute(DeleteDocumentTypeInput(document_type_id="type-1"))

    assert raised.value.document_count == 1
    assert types.get("type-1") is not None


def test_a_document_of_another_type_does_not_hold_this_one_back():
    use_case, types = _delete(stored=[_type()], documents=[_document("type-2")])

    use_case.execute(DeleteDocumentTypeInput(document_type_id="type-1"))

    assert types.get("type-1") is None


def test_an_unclassified_document_does_not_hold_any_type_back():
    """Its type is null, so nothing it shows depends on one existing."""
    use_case, types = _delete(stored=[_type()], documents=[_document(None)])

    use_case.execute(DeleteDocumentTypeInput(document_type_id="type-1"))

    assert types.get("type-1") is None


def test_deleting_a_type_that_does_not_exist_says_so():
    """Rather than reading as a job well done, which is what a silent success
    would make of a stale screen or a mistyped id."""
    use_case, _ = _delete()

    with pytest.raises(DocumentTypeNotFound):
        use_case.execute(DeleteDocumentTypeInput(document_type_id="gone"))
