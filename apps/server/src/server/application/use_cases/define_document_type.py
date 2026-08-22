import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import DocumentType
from server.domain.ports import (
    DocumentContent,
    DocumentTypeConfigurator,
    DocumentTypeRepository,
)


@dataclass(frozen=True, slots=True)
class DefineDocumentTypeInput:
    name: str
    description: str
    sample_document: DocumentContent


class DefineDocumentType:
    """Config > Document type: an AI inspects a sample document and proposes the
    extraction prompt + schema for that type (e.g. "Bancolombia statement")."""

    def __init__(
        self,
        configurator: DocumentTypeConfigurator,
        document_types: DocumentTypeRepository,
    ) -> None:
        self._configurator = configurator
        self._document_types = document_types

    def execute(self, data: DefineDocumentTypeInput) -> DocumentType:
        proposal = self._configurator.propose_config(data.sample_document, data.name)
        document_type = DocumentType(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            extraction_prompt=proposal.extraction_prompt,
            extraction_schema=proposal.extraction_schema,
            active=True,
            created_at=datetime.now(UTC),
        )
        self._document_types.save(document_type)
        return document_type
