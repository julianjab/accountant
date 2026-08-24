from dataclasses import dataclass

from server.application.use_cases.update_document_type import DocumentTypeNotFound
from server.domain.ports import DocumentRepository, DocumentTypeRepository


class DocumentTypeInUse(Exception):
    """Raised when documents were already classified as the type being deleted.

    Carries the count because the caller has to be told how much is at stake:
    "3 documents use this type" is a decision they can make, "cannot delete"
    is not.
    """

    def __init__(self, document_type_id: str, document_count: int) -> None:
        self.document_type_id = document_type_id
        self.document_count = document_count
        super().__init__(
            f"{document_count} document(s) are classified as {document_type_id}; "
            "deactivate the type instead of deleting it"
        )


@dataclass(frozen=True, slots=True)
class DeleteDocumentTypeInput:
    document_type_id: str


class DeleteDocumentType:
    """Removes a document type, if nothing was ever filed under it.

    Deleting is for undoing a mistake — a duplicate, a type configured against
    the wrong sample. It is not how a type is retired: `active` already does
    that, and it keeps every document that was classified under it readable.

    A type with documents is therefore refused rather than cascaded. Those
    documents keep an id pointing at nothing: the screen can no longer say
    what kind of paper each one is, their extracted fields lose the labels
    that made them legible, and the reconciliation loses the mapping that made
    their figures comparable — with no record anywhere of what was lost. That
    is a worse outcome than a delete that did not happen, and the accountant
    has `active` for what they actually meant.
    """

    def __init__(
        self,
        document_types: DocumentTypeRepository,
        documents: DocumentRepository,
    ) -> None:
        self._document_types = document_types
        self._documents = documents

    def execute(self, data: DeleteDocumentTypeInput) -> None:
        if self._document_types.get(data.document_type_id) is None:
            # Distinguished from a successful delete on purpose: a 404 tells
            # the caller their view is stale, where a silent success would let
            # a wrong id read as a job well done.
            raise DocumentTypeNotFound(f"Document type {data.document_type_id} not found")

        in_use = self._documents.list_by_document_type(data.document_type_id)
        if in_use:
            raise DocumentTypeInUse(data.document_type_id, len(in_use))

        self._document_types.delete(data.document_type_id)
