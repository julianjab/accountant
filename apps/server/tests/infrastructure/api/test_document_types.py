from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import DocumentType
from server.infrastructure.api.deps import get_document_type_repository
from server.main import app


@pytest.fixture
def document_types():
    get_document_type_repository.cache_clear()
    yield get_document_type_repository()
    get_document_type_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
