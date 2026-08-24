"""Deleting a type and the reconciliation configuration attached to it.

Intake owns the type and reconciliation owns the mapping, and neither context
may import the other — so the step that joins them lives at the composition
edge. It is a named unit rather than a couple of lines in a router because a
router is not somewhere a rule can be tested, and the next delete path would
have to remember it.
"""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import DeleteDocumentType, DocumentTypeInUse
from server.domain.entities import Document, DocumentStatus, DocumentType
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
)
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.infrastructure import (
    DeleteDocumentTypeAndMappings,
    InMemoryConceptMappingRepository,
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


def _mapping(type_id: str, kind_id: str) -> ConceptMapping:
    return ConceptMapping(
        document_type_id=type_id,
        kind_id=kind_id,
        reporter_path="nit",
        entries=(ConceptMappingEntry("saldo", "bank:cert_saldo_cuentas_ahorro"),),
    )


def _document(document_type_id: str) -> Document:
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


def _build(*, types=(), documents=(), mappings=()):
    type_repo = InMemoryDocumentTypeRepository()
    for document_type in types:
        type_repo.save(document_type)
    document_repo = InMemoryDocumentRepository()
    for document in documents:
        document_repo.save(document)
    mapping_repo = InMemoryConceptMappingRepository()
    for mapping in mappings:
        mapping_repo.save(mapping)
    use_case = DeleteDocumentTypeAndMappings(
        DeleteDocumentType(type_repo, document_repo), mapping_repo
    )
    return use_case, type_repo, mapping_repo


def test_the_mapping_goes_with_the_type():
    """Left behind it is unreachable — nothing lists mappings for a type that
    does not exist — and would attach to a type that reused the id."""
    use_case, types, mappings = _build(
        types=[_type()], mappings=[_mapping("type-1", "exogena_dian")]
    )

    use_case.execute("type-1")

    assert types.get("type-1") is None
    assert mappings.get("type-1", "exogena_dian") is None


def test_every_kind_the_type_was_mapped_for_is_cleared():
    """A type can answer more than one reconciliation model, and deleting only
    the one the caller happened to name would leave the others orphaned."""
    use_case, _, mappings = _build(
        types=[_type()],
        mappings=[_mapping("type-1", "exogena_dian"), _mapping("type-1", "otra")],
    )

    use_case.execute("type-1")

    assert mappings.list_for_kind("exogena_dian") == []
    assert mappings.list_for_kind("otra") == []


def test_another_type_keeps_its_mapping():
    use_case, _, mappings = _build(
        types=[_type(), _type("type-2")],
        mappings=[_mapping("type-1", "exogena_dian"), _mapping("type-2", "exogena_dian")],
    )

    use_case.execute("type-1")

    assert mappings.get("type-2", "exogena_dian") is not None


def test_a_refused_delete_leaves_the_mapping_alone():
    """The type survives because documents are filed under it, so its mapping
    has to survive too — otherwise the refusal still half-happened, and the
    type would extract fields that reconcile against nothing."""
    use_case, types, mappings = _build(
        types=[_type()],
        documents=[_document("type-1")],
        mappings=[_mapping("type-1", "exogena_dian")],
    )

    with pytest.raises(DocumentTypeInUse):
        use_case.execute("type-1")

    assert types.get("type-1") is not None
    assert mappings.get("type-1", "exogena_dian") is not None


def test_a_mapping_that_cannot_be_deleted_does_not_undo_a_deleted_type():
    """There is no transaction across the two contexts. Failing here would
    report an error for work that succeeded, over a mapping nothing can reach.
    """

    class _Failing(InMemoryConceptMappingRepository):
        def delete_for_document_type(self, document_type_id: str) -> None:
            raise RuntimeError("firestore is down")

    types = InMemoryDocumentTypeRepository()
    types.save(_type())
    use_case = DeleteDocumentTypeAndMappings(
        DeleteDocumentType(types, InMemoryDocumentRepository()), _Failing()
    )

    use_case.execute("type-1")

    assert types.get("type-1") is None
