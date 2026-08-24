from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import DocumentType
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import get_document_type_repository
from server.main import app


@pytest.fixture
def document_types():
    get_document_type_repository.cache_clear()
    yield get_document_type_repository()
    get_document_type_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[require_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _document_type(**overrides) -> DocumentType:
    defaults = dict(
        id="type-1",
        name="Bancolombia statement",
        description="Bank statement",
        extraction_prompt="Extract fields",
        extraction_schema={"type": "object", "properties": {}},
        active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return DocumentType(**defaults)


def test_list_document_types_defaults_to_active_only(client, document_types) -> None:
    document_types.save(_document_type(id="type-1", active=True))
    document_types.save(_document_type(id="type-2", active=False))

    response = client.get("/document-types")

    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert ids == ["type-1"]


def test_list_document_types_with_active_only_false(client, document_types) -> None:
    document_types.save(_document_type(id="type-1", active=True))
    document_types.save(_document_type(id="type-2", active=False))

    response = client.get("/document-types", params={"active_only": "false"})

    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert ids == {"type-1", "type-2"}


class _FailingMappingRepository:
    def save(self, mapping):
        raise RuntimeError("Firestore is unavailable")

    def get(self, document_type_id, kind_id):
        return None

    def list_for_kind(self, kind_id):
        return []


def test_a_mapping_that_cannot_be_stored_is_reported_not_raised() -> None:
    """The type is already saved and there is no transaction across the two
    contexts, so a 500 here would report an error while leaving the type
    created and hide that its mapping is missing."""
    from server.application.use_cases import DefinedDocumentType, DefineDocumentType
    from server.domain.ports import ProposedFieldMapping
    from server.infrastructure.api import deps
    from server.reconciliation.application import SaveConceptMapping

    document_type = DocumentType(
        id="t-1",
        name="Certificado",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime.now(UTC),
    )

    class _UseCase(DefineDocumentType):
        def __init__(self):
            pass

        def execute(self, data):
            return DefinedDocumentType(
                document_type=document_type,
                field_mappings=(ProposedFieldMapping("saldo", "bank:cert_saldo_cuentas_ahorro"),),
                unmapped_fields=(),
                reporter_path="nit",
            )

    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_define_document_type_use_case] = lambda: _UseCase()
    app.dependency_overrides[deps.get_save_concept_mapping_use_case] = lambda: SaveConceptMapping(
        deps.get_reconciliation_registry(), _FailingMappingRepository()
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/document-types",
            data={"name": "Certificado", "description": "d"},
            files={"sample_file": ("s.pdf", b"%PDF-", "application/pdf")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["field_mappings"] == []
        assert body["unmapped_fields"] == [
            {
                "field_path": "saldo",
                "reason": "the mapping could not be stored; set it again to retry",
            }
        ]
    finally:
        app.dependency_overrides.clear()


def test_a_mapping_with_no_reporting_party_is_not_stored() -> None:
    """Every fact needs a party to attribute it to, so the projection discards
    such a mapping whole. Storing it would leave the type looking configured
    and every claim reported as missing with nothing pointing at the cause."""
    from server.application.use_cases import DefinedDocumentType, DefineDocumentType
    from server.domain.ports import ProposedFieldMapping
    from server.infrastructure.api import deps

    document_type = DocumentType(
        id="t-2",
        name="Certificado",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime.now(UTC),
    )

    class _UseCase(DefineDocumentType):
        def __init__(self):
            pass

        def execute(self, data):
            return DefinedDocumentType(
                document_type=document_type,
                field_mappings=(ProposedFieldMapping("saldo", "bank:cert_saldo_cuentas_ahorro"),),
                unmapped_fields=(),
                reporter_path=None,
            )

    deps.get_concept_mapping_repository.cache_clear()
    mappings = deps.get_concept_mapping_repository()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_define_document_type_use_case] = lambda: _UseCase()
    try:
        response = TestClient(app).post(
            "/document-types",
            data={"name": "Certificado", "description": "d"},
            files={"sample_file": ("s.pdf", b"%PDF-", "application/pdf")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["field_mappings"] == []
        assert body["unmapped_fields"] == [
            {
                "field_path": "saldo",
                "reason": "the document does not say who reports these amounts",
            }
        ]
        assert mappings.get("t-2", "exogena_dian") is None
    finally:
        app.dependency_overrides.clear()
        deps.get_concept_mapping_repository.cache_clear()
