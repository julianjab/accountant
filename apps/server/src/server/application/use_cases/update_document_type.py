from dataclasses import dataclass, replace
from typing import Any

from server.domain.entities import DocumentType
from server.domain.ports import DocumentTypeRepository


class DocumentTypeNotFound(Exception):
    """Raised when the document type to update does not exist."""


@dataclass(frozen=True, slots=True)
class UpdateDocumentTypeInput:
    """A partial edit: every field left as None keeps its stored value.

    None is unambiguous here because none of the target fields is nullable on
    the entity, so "clear this" is not a request that can be made — the only
    reading of an absent field is "do not touch it".
    """

    document_type_id: str
    name: str | None = None
    description: str | None = None
    active: bool | None = None
    extraction_prompt: str | None = None
    extraction_schema: dict[str, Any] | None = None


class UpdateDocumentType:
    """Config > Document type: edits a type the AI already proposed.

    The proposal is a starting point, not a verdict — it routinely extracts
    more fields than the accountant cares about — so trimming the schema and
    rewording the prompt has to be possible without re-uploading a sample and
    paying for a second AI pass.
    """

    def __init__(self, document_types: DocumentTypeRepository) -> None:
        self._document_types = document_types

    def execute(self, data: UpdateDocumentTypeInput) -> DocumentType:
        stored = self._document_types.get(data.document_type_id)
        if stored is None:
            raise DocumentTypeNotFound(f"Document type {data.document_type_id} not found")

        changes = {
            field: value
            for field, value in (
                ("name", data.name),
                ("description", data.description),
                ("active", data.active),
                ("extraction_prompt", data.extraction_prompt),
                ("extraction_schema", data.extraction_schema),
            )
            if value is not None
        }
        updated = replace(stored, **changes)
        self._document_types.save(updated)
        return updated
