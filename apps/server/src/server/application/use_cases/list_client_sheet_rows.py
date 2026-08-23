from dataclasses import dataclass

from server.domain.entities import DocumentStatus, SheetRow
from server.domain.ports import ClientRepository, DocumentRepository, ExtractedDataRepository


class ClientNotFound(Exception):
    """Raised when the client to list sheet rows for does not exist."""


@dataclass(frozen=True, slots=True)
class ListClientSheetRowsInput:
    client_id: str


class ListClientSheetRows:
    """Consolidates the approved documents of a client into spreadsheet rows.

    A row's fields are read from `ExtractedData.fields` by the canonical keys
    (`date`, `description`, `amount`, `tax`); a document type whose
    `extraction_schema` uses different keys yields an empty value for that
    column until document types can declare a mapping onto this shape.
    """

    def __init__(
        self,
        clients: ClientRepository,
        documents: DocumentRepository,
        extracted_data: ExtractedDataRepository,
    ) -> None:
        self._clients = clients
        self._documents = documents
        self._extracted_data = extracted_data

    def execute(self, data: ListClientSheetRowsInput) -> list[SheetRow]:
        if self._clients.get(data.client_id) is None:
            raise ClientNotFound(f"Client {data.client_id} not found")

        approved_documents = [
            document
            for document in self._documents.list_by_client(data.client_id)
            if document.status == DocumentStatus.APPROVED
        ]

        rows = []
        for document in approved_documents:
            extracted = self._extracted_data.get_by_document(document.id)
            fields = extracted.fields if extracted is not None else {}
            rows.append(
                SheetRow(
                    source_document_id=document.id,
                    source_document_file_name=document.file_name,
                    date=str(fields.get("date", "")),
                    description=str(fields.get("description", "")),
                    amount=str(fields.get("amount", "")),
                    tax=str(fields.get("tax", "")),
                )
            )
        return rows
