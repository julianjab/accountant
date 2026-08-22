from server.domain.entities import Client, Document, DocumentType, ExtractedData


class InMemoryClientRepository:
    def __init__(self) -> None:
        self._items: dict[str, Client] = {}

    def save(self, client: Client) -> None:
        self._items[client.id] = client

    def get(self, client_id: str) -> Client | None:
        return self._items.get(client_id)

    def list_all(self) -> list[Client]:
        return list(self._items.values())


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._items: dict[str, Document] = {}

    def save(self, document: Document) -> None:
        self._items[document.id] = document

    def get(self, document_id: str) -> Document | None:
        return self._items.get(document_id)

    def list_by_client(self, client_id: str) -> list[Document]:
        return [d for d in self._items.values() if d.client_id == client_id]


class InMemoryDocumentTypeRepository:
    def __init__(self) -> None:
        self._items: dict[str, DocumentType] = {}

    def save(self, document_type: DocumentType) -> None:
        self._items[document_type.id] = document_type

    def get(self, document_type_id: str) -> DocumentType | None:
        return self._items.get(document_type_id)

    def list_active(self) -> list[DocumentType]:
        return [t for t in self._items.values() if t.active]


class InMemoryExtractedDataRepository:
    def __init__(self) -> None:
        self._items: dict[str, ExtractedData] = {}

    def save(self, extracted_data: ExtractedData) -> None:
        self._items[extracted_data.document_id] = extracted_data

    def get_by_document(self, document_id: str) -> ExtractedData | None:
        return self._items.get(document_id)
