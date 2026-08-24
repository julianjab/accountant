from dataclasses import dataclass

from server.application.use_cases.approve_document import DocumentNotFound
from server.domain.ports import DocumentContent, DocumentRepository, DocumentStorage


@dataclass(frozen=True, slots=True)
class ReadStoredDocumentInput:
    document_id: str


class ReadStoredDocument:
    """Fetches the bytes of a document already in the system.

    Configuring a document type needs a sample, and the natural sample is a
    paper the accountant already put in a client's folder — it is the same
    kind of document every future document of that type will be. Uploading a
    loose copy from a laptop instead leaves the type pointing at bytes nobody
    can retrieve, so the configuration can never be checked against the page
    it came from.

    Metadata and file live apart on purpose: the repository knows which Drive
    file a document is, and the storage knows how to read it. This is the one
    place that needs both.
    """

    def __init__(self, documents: DocumentRepository, storage: DocumentStorage) -> None:
        self._documents = documents
        self._storage = storage

    def execute(self, data: ReadStoredDocumentInput) -> DocumentContent:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")
        return self._storage.download(document.drive_file_id)
