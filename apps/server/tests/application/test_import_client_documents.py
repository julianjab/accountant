"""Backfilling the files that were already in a client's folder."""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    ClientHasNoFolder,
    ClientNotFound,
    ImportClientDocuments,
    ImportClientDocumentsInput,
    ProcessUploadedDocument,
)
from server.domain.entities import Client, Document, DocumentStatus, DocumentType
from server.domain.ports import DocumentContent, StoredFile
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryClientRepository,
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryExtractedDataRepository,
)

NOW = datetime.now(UTC)

_TYPE = DocumentType(
    id="type-1",
    name="Certificado",
    description="Certificado tributario",
    extraction_prompt="Extract the balance.",
    extraction_schema={"type": "object", "properties": {}},
    active=True,
    created_at=NOW,
)


class _Storage:
    def __init__(self, files: list[StoredFile], unreadable: set[str] | None = None) -> None:
        self._files = files
        self._unreadable = unreadable or set()
        self.listed: list[str] = []

    def list_files(self, folder_reference: str) -> list[StoredFile]:
        self.listed.append(folder_reference)
        return self._files

    def download(self, file_reference: str) -> DocumentContent:
        if file_reference in self._unreadable:
            raise RuntimeError("Drive is unavailable")
        return DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="f.pdf")


class _Classifier:
    def __init__(self, result=_TYPE) -> None:
        self._result = result

    def classify(self, content, available_types):
        return self._result


class _Ocr:
    def extract(self, content, document_type):
        return {"saldo": "10"}


def _use_case(storage, classifier=None, clients=None, documents=None):
    clients = clients or InMemoryClientRepository()
    documents = documents or InMemoryDocumentRepository()
    types = InMemoryDocumentTypeRepository()
    types.save(_TYPE)
    process = ProcessUploadedDocument(
        storage=storage,
        classifier=classifier or _Classifier(),
        ocr=_Ocr(),
        documents=documents,
        document_types=types,
        extracted_data=InMemoryExtractedDataRepository(),
    )
    return (
        ImportClientDocuments(
            clients=clients, documents=documents, storage=storage, process_document=process
        ),
        clients,
        documents,
    )


def _client(folder_id: str | None = "folder-1") -> Client:
    return Client(
        id="c1",
        name="Cliente",
        tax_id="79999999",
        email=None,
        created_at=NOW,
        drive_folder_id=folder_id,
    )


def _files(*ids: str) -> list[StoredFile]:
    return [StoredFile(id=i, name=f"{i}.pdf", mime_type="application/pdf") for i in ids]


def test_every_file_already_in_the_folder_becomes_a_document():
    """The gap this closes: change notifications only report what arrives
    after a subscription, so these files were invisible forever."""
    storage = _Storage(_files("f1", "f2", "f3"))
    use_case, clients, documents = _use_case(storage)
    clients.save(_client())

    result = use_case.execute(ImportClientDocumentsInput(client_id="c1"))

    assert len(result.imported) == 3
    assert result.skipped == 0
    assert result.failed == []
    assert storage.listed == ["folder-1"]
    assert {d.status for d in result.imported} == {DocumentStatus.PROCESSED}
    assert len(documents.list_by_client("c1")) == 3


def test_running_the_import_twice_does_not_reprocess_what_succeeded():
    """Imports are re-run whenever a client is opened, and OCR is the
    expensive part."""
    storage = _Storage(_files("f1", "f2"))
    use_case, clients, _ = _use_case(storage)
    clients.save(_client())

    use_case.execute(ImportClientDocumentsInput(client_id="c1"))
    second = use_case.execute(ImportClientDocumentsInput(client_id="c1"))

    assert second.imported == []
    assert second.skipped == 2


def test_reprocess_forces_documents_through_again():
    storage = _Storage(_files("f1"))
    use_case, clients, _ = _use_case(storage)
    clients.save(_client())

    use_case.execute(ImportClientDocumentsInput(client_id="c1"))
    again = use_case.execute(ImportClientDocumentsInput(client_id="c1", reprocess=True))

    assert len(again.imported) == 1
    assert again.skipped == 0


def test_a_file_that_failed_before_is_retried():
    """A skip is earned by succeeding; a FAILED document is not an outcome to
    preserve across an explicit re-import."""
    storage = _Storage(_files("f1"))
    use_case, clients, documents = _use_case(storage, classifier=_Classifier(result=None))
    clients.save(_client())

    first = use_case.execute(ImportClientDocumentsInput(client_id="c1"))
    assert len(first.failed) == 1

    second = use_case.execute(ImportClientDocumentsInput(client_id="c1"))
    assert second.skipped == 0
    assert len(second.failed) == 1
    # The retry reuses the row rather than piling up one per attempt.
    assert len(documents.list_by_client("c1")) == 1


def test_one_unreadable_file_does_not_abandon_the_rest_of_the_folder():
    storage = _Storage(_files("f1", "f2", "f3"), unreadable={"f2"})
    use_case, clients, _ = _use_case(storage)
    clients.save(_client())

    result = use_case.execute(ImportClientDocumentsInput(client_id="c1"))

    assert {d.drive_file_id for d in result.imported} == {"f1", "f3"}


def test_an_empty_folder_imports_nothing_without_failing():
    storage = _Storage([])
    use_case, clients, _ = _use_case(storage)
    clients.save(_client())

    result = use_case.execute(ImportClientDocumentsInput(client_id="c1"))

    assert (result.imported, result.failed, result.skipped) == ([], [], 0)


def test_an_unknown_client_is_refused():
    use_case, _, _ = _use_case(_Storage([]))
    with pytest.raises(ClientNotFound):
        use_case.execute(ImportClientDocumentsInput(client_id="nope"))


@pytest.mark.parametrize("folder_id", [None, ""])
def test_a_client_with_no_folder_is_refused(folder_id):
    """Silently importing nothing would read as "the folder is empty"."""
    use_case, clients, _ = _use_case(_Storage([]))
    clients.save(_client(folder_id=folder_id))
    with pytest.raises(ClientHasNoFolder):
        use_case.execute(ImportClientDocumentsInput(client_id="c1"))


def test_documents_from_other_clients_are_untouched():
    storage = _Storage(_files("f1"))
    documents = InMemoryDocumentRepository()
    documents.save(
        Document(
            id="other",
            client_id="c2",
            document_type_id=None,
            drive_file_id="f1",
            file_name="f.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            error=None,
            created_at=NOW,
        )
    )
    use_case, clients, _ = _use_case(storage, documents=documents)
    clients.save(_client())

    result = use_case.execute(ImportClientDocumentsInput(client_id="c1"))

    # The same Drive file can sit in two clients' folders; one client's
    # processed document must not suppress the other's import.
    assert len(result.imported) == 1
    assert result.skipped == 0


def test_reprocess_rewrites_the_document_instead_of_adding_a_second_one():
    """A file has one document. Without this, every forced re-import would
    leave another row behind for the same Drive file."""
    storage = _Storage(_files("f1"))
    use_case, clients, documents = _use_case(storage)
    clients.save(_client())

    first = use_case.execute(ImportClientDocumentsInput(client_id="c1"))
    again = use_case.execute(ImportClientDocumentsInput(client_id="c1", reprocess=True))

    assert len(documents.list_by_client("c1")) == 1
    assert again.imported[0].id == first.imported[0].id


def test_an_approved_document_is_never_reprocessed():
    """Approval is a person's review. Re-running OCR would reset it to
    CLASSIFYING and drop the approval with no record it ever happened."""
    storage = _Storage(_files("f1"))
    documents = InMemoryDocumentRepository()
    use_case, clients, _ = _use_case(storage, documents=documents)
    clients.save(_client())

    imported = use_case.execute(ImportClientDocumentsInput(client_id="c1")).imported[0]
    approved = Document(
        id=imported.id,
        client_id="c1",
        document_type_id=imported.document_type_id,
        drive_file_id="f1",
        file_name=imported.file_name,
        mime_type=imported.mime_type,
        status=DocumentStatus.APPROVED,
        error=None,
        created_at=imported.created_at,
        approved_by="preparer@example.com",
    )
    documents.save(approved)

    result = use_case.execute(ImportClientDocumentsInput(client_id="c1", reprocess=True))

    assert result.skipped == 1
    assert result.imported == []
    still = documents.get_by_drive_file_id_and_client("f1", "c1")
    assert still.status == DocumentStatus.APPROVED
    assert still.approved_by == "preparer@example.com"
