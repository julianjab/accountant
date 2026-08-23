from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import (
    ApproveDocument,
    ApproveDocumentInput,
    DocumentNotApprovable,
    DocumentNotFound,
    GetExtractedData,
)
from server.domain.entities import DocumentStatus
from server.infrastructure.api.deps import (
    get_approve_document_use_case,
    get_document_repository,
    get_extracted_data_use_case,
)
from server.infrastructure.api.schemas import (
    DocumentApproveRequest,
    DocumentMetricsResponse,
    DocumentResponse,
    ExtractedDataResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])

_UNPROCESSED_STATUSES = {
    DocumentStatus.PENDING,
    DocumentStatus.CLASSIFYING,
    DocumentStatus.RUNNING_OCR,
}


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    status: DocumentStatus | None = None,
    client_id: str | None = None,
    documents=Depends(get_document_repository),
) -> list[DocumentResponse]:
    items = documents.list_all(status=status)
    if client_id is not None:
        items = [d for d in items if d.client_id == client_id]
    return [DocumentResponse.model_validate(d, from_attributes=True) for d in items]


@router.get("/metrics", response_model=DocumentMetricsResponse)
def get_document_metrics(documents=Depends(get_document_repository)) -> DocumentMetricsResponse:
    items = documents.list_all()
    today = datetime.now(UTC).date()

    unprocessed = sum(1 for d in items if d.status in _UNPROCESSED_STATUSES)
    failed = sum(1 for d in items if d.status == DocumentStatus.FAILED)
    processed = [d for d in items if d.status == DocumentStatus.PROCESSED]
    processed_today = sum(
        1
        for d in processed
        if d.processed_at is not None and d.processed_at.astimezone(UTC).date() == today
    )

    durations = [
        (d.processed_at - d.created_at).total_seconds()
        for d in processed
        if d.processed_at is not None
    ]
    avg_processing_seconds = sum(durations) / len(durations) if durations else None

    return DocumentMetricsResponse(
        unprocessed=unprocessed,
        processed_today=processed_today,
        failed=failed,
        avg_processing_seconds=avg_processing_seconds,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, documents=Depends(get_document_repository)) -> DocumentResponse:
    document = documents.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.get("/{document_id}/extracted-data", response_model=ExtractedDataResponse)
def get_document_extracted_data(
    document_id: str,
    use_case: GetExtractedData = Depends(get_extracted_data_use_case),
) -> ExtractedDataResponse:
    extracted_data = use_case.execute(document_id)
    if extracted_data is None:
        raise HTTPException(status_code=404, detail="Extracted data not found")
    return ExtractedDataResponse.model_validate(extracted_data, from_attributes=True)


@router.post("/{document_id}/approve", response_model=DocumentResponse)
def approve_document(
    document_id: str,
    payload: DocumentApproveRequest | None = None,
    use_case: ApproveDocument = Depends(get_approve_document_use_case),
) -> DocumentResponse:
    approved_by = payload.approved_by if payload is not None else None
    try:
        document = use_case.execute(
            ApproveDocumentInput(document_id=document_id, approved_by=approved_by)
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentNotApprovable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DocumentResponse.model_validate(document, from_attributes=True)
