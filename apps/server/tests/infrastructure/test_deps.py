"""The repository providers are the one place the persistence backend is chosen."""

import pytest

from server.infrastructure.adapters import firestore_repositories, in_memory_repositories
from server.infrastructure.api import deps


@pytest.fixture(autouse=True)
def clear_caches():
    # Every provider here is lru_cached, so the backend decision sticks.
    for provider in (
        deps.get_settings,
        deps.get_firestore,
        deps.get_client_repository,
        deps.get_document_repository,
        deps.get_document_type_repository,
        deps.get_extracted_data_repository,
        deps.get_session_repository,
    ):
        provider.cache_clear()
    yield
    for provider in (
        deps.get_settings,
        deps.get_firestore,
        deps.get_client_repository,
        deps.get_document_repository,
        deps.get_document_type_repository,
        deps.get_extracted_data_repository,
        deps.get_session_repository,
    ):
        provider.cache_clear()


def test_no_firestore_project_falls_back_to_in_memory(monkeypatch):
    monkeypatch.setattr(deps.get_settings(), "firestore_project", "")
    deps.get_firestore.cache_clear()

    assert deps.get_firestore() is None
    assert isinstance(deps.get_client_repository(), in_memory_repositories.InMemoryClientRepository)
    assert isinstance(
        deps.get_document_repository(), in_memory_repositories.InMemoryDocumentRepository
    )
    assert isinstance(
        deps.get_document_type_repository(),
        in_memory_repositories.InMemoryDocumentTypeRepository,
    )
    assert isinstance(
        deps.get_extracted_data_repository(),
        in_memory_repositories.InMemoryExtractedDataRepository,
    )
    assert isinstance(
        deps.get_session_repository(), in_memory_repositories.InMemorySessionRepository
    )


def test_a_configured_project_selects_firestore(monkeypatch):
    class FakeDb:
        def collection(self, name: str) -> object:
            return object()

    monkeypatch.setattr(deps, "get_firestore", lambda: FakeDb())

    assert isinstance(
        deps.get_client_repository.__wrapped__(), firestore_repositories.FirestoreClientRepository
    )
    assert isinstance(
        deps.get_document_repository.__wrapped__(),
        firestore_repositories.FirestoreDocumentRepository,
    )
    assert isinstance(
        deps.get_document_type_repository.__wrapped__(),
        firestore_repositories.FirestoreDocumentTypeRepository,
    )
    assert isinstance(
        deps.get_extracted_data_repository.__wrapped__(),
        firestore_repositories.FirestoreExtractedDataRepository,
    )
    assert isinstance(
        deps.get_session_repository.__wrapped__(),
        firestore_repositories.FirestoreSessionRepository,
    )


def test_firestore_client_is_built_from_the_configured_project(monkeypatch):
    captured = {}

    class FakeFirestoreClient:
        def __init__(self, project: str, database: str) -> None:
            captured["project"] = project
            captured["database"] = database

    monkeypatch.setattr(deps, "FirestoreClient", FakeFirestoreClient)
    monkeypatch.setattr(deps.get_settings(), "firestore_project", "proj")
    monkeypatch.setattr(deps.get_settings(), "firestore_database", "db")
    deps.get_firestore.cache_clear()

    assert isinstance(deps.get_firestore(), FakeFirestoreClient)
    assert captured == {"project": "proj", "database": "db"}
