from dataclasses import dataclass
from typing import Any, Protocol

from server.domain.entities import DocumentType
from server.domain.ports.document_storage import DocumentContent


class DocumentClassifier(Protocol):
    """Fast AI: given a document and the available document types, picks the right one."""

    def classify(
        self, content: DocumentContent, available_types: list[DocumentType]
    ) -> DocumentType | None: ...


class OcrEngine(Protocol):
    """Runs the OCR/extraction configured for a document type."""

    def extract(self, content: DocumentContent, document_type: DocumentType) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ProposedOcrConfig:
    extraction_prompt: str
    extraction_schema: dict[str, Any]


class DocumentTypeConfigurator(Protocol):
    """AI that, given a sample document, proposes the extraction prompt + schema
    for a new document type (Config > Document type)."""

    def propose_config(self, content: DocumentContent, type_name: str) -> ProposedOcrConfig: ...
