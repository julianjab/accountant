from datetime import UTC, datetime

from server.application.use_cases import ProcessUploadedDocument, ProcessUploadedDocumentInput
from server.domain.entities import DocumentStatus, DocumentType
from server.domain.ports import DocumentContent
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryExtractedDataRepository,
)

_SAMPLE_TYPE = DocumentType(
    id="type-1",
    name="Bancolombia statement",
    description="Bank statement issued by Bancolombia",
    extraction_prompt="Extract the account number and balance.",
    extraction_schema={"type": "object", "properties": {}},
    active=True,
    created_at=datetime.now(UTC),
)


class _FakeStorage:
    def download(self, file_reference: str) -> DocumentContent:
        return DocumentContent(data=b"pdf-bytes", mime_type="application/pdf", file_name="doc.pdf")


class _FakeClassifier:
    def __init__(self, result: DocumentType | None) -> None:
        self._result = result

    def classify(self, content, available_types):
        return self._result


class _FakeOcrEngine:
    def extract(self, content, document_type):
        return {"account_number": "123", "balance": 1000}


def _use_case(classifier_result: DocumentType | None) -> ProcessUploadedDocument:
    document_types = InMemoryDocumentTypeRepository()
    document_types.save(_SAMPLE_TYPE)

    return ProcessUploadedDocument(
        storage=_FakeStorage(),
        classifier=_FakeClassifier(classifier_result),
        ocr=_FakeOcrEngine(),
        documents=InMemoryDocumentRepository(),
        document_types=document_types,
        extracted_data=InMemoryExtractedDataRepository(),
    )


def test_process_uploaded_document_extracts_data_when_type_is_recognized() -> None:
    use_case = _use_case(classifier_result=_SAMPLE_TYPE)

    document = use_case.execute(
        ProcessUploadedDocumentInput(
            client_id="client-1", drive_file_id="drive-1", file_reference="ref-1"
        )
    )

    assert document.status == DocumentStatus.PROCESSED
    assert document.document_type_id == _SAMPLE_TYPE.id


def test_process_uploaded_document_fails_when_type_is_unknown() -> None:
    use_case = _use_case(classifier_result=None)

    document = use_case.execute(
        ProcessUploadedDocumentInput(
            client_id="client-1", drive_file_id="drive-1", file_reference="ref-1"
        )
    )

    assert document.status == DocumentStatus.FAILED
    assert document.error is not None
