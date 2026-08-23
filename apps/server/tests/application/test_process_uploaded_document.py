from datetime import UTC, datetime

import pytest

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
    def __init__(self, raises: Exception | None = None) -> None:
        self._raises = raises

    def download(self, file_reference: str) -> DocumentContent:
        if self._raises is not None:
            raise self._raises
        return DocumentContent(data=b"pdf-bytes", mime_type="application/pdf", file_name="doc.pdf")


class _FakeClassifier:
    def __init__(self, result: DocumentType | None, raises: Exception | None = None) -> None:
        self._result = result
        self._raises = raises

    def classify(self, content, available_types):
        if self._raises is not None:
            raise self._raises
        return self._result


class _FakeOcrEngine:
    def __init__(self, raises: Exception | None = None) -> None:
        self._raises = raises

    def extract(self, content, document_type):
        if self._raises is not None:
            raise self._raises
        return {"account_number": "123", "balance": 1000}


def _use_case(
    classifier_result: DocumentType | None = None,
    storage: _FakeStorage | None = None,
    classifier: _FakeClassifier | None = None,
    ocr: _FakeOcrEngine | None = None,
    documents: InMemoryDocumentRepository | None = None,
) -> ProcessUploadedDocument:
    document_types = InMemoryDocumentTypeRepository()
    document_types.save(_SAMPLE_TYPE)

    return ProcessUploadedDocument(
        storage=storage or _FakeStorage(),
        classifier=classifier or _FakeClassifier(classifier_result),
        ocr=ocr or _FakeOcrEngine(),
        documents=documents or InMemoryDocumentRepository(),
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


def test_a_download_failure_propagates_without_persisting_anything() -> None:
    # Nothing has been created yet at this point, so a caller is free to
    # treat this as "safe to retry" without risking a duplicate document.
    documents = InMemoryDocumentRepository()
    use_case = _use_case(
        storage=_FakeStorage(raises=RuntimeError("network error")), documents=documents
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            ProcessUploadedDocumentInput(
                client_id="client-1", drive_file_id="drive-1", file_reference="ref-1"
            )
        )

    assert documents.list_by_client("client-1") == []


def test_a_classifier_failure_is_turned_into_a_failed_document_instead_of_raising() -> None:
    # A row was already persisted (CLASSIFYING) by this point: raising here
    # would leave it stuck forever with no visible error and no safe retry.
    use_case = _use_case(classifier=_FakeClassifier(None, raises=RuntimeError("Anthropic 503")))

    document = use_case.execute(
        ProcessUploadedDocumentInput(
            client_id="client-1", drive_file_id="drive-1", file_reference="ref-1"
        )
    )

    assert document.status == DocumentStatus.FAILED
    assert document.error == "Anthropic 503"


def test_an_ocr_failure_is_turned_into_a_failed_document_instead_of_raising() -> None:
    use_case = _use_case(
        classifier_result=_SAMPLE_TYPE, ocr=_FakeOcrEngine(raises=RuntimeError("Anthropic timeout"))
    )

    document = use_case.execute(
        ProcessUploadedDocumentInput(
            client_id="client-1", drive_file_id="drive-1", file_reference="ref-1"
        )
    )

    assert document.status == DocumentStatus.FAILED
    assert document.error == "Anthropic timeout"
