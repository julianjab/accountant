from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import (
    ApproveDocumentInput,
    DocumentNotExtractable,
    DocumentNotFound,
    GetDocumentMetrics,
    GetExtractedData,
    ReprocessDocumentInput,
)
from server.domain.entities import DocumentStatus
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_approve_document_use_case,
    get_document_metrics_use_case,
    get_document_repository,
    get_extracted_data_use_case,
    get_reprocess_document_use_case,
)
from server.infrastructure.api.schemas import (
    DocumentApproveRequest,
    DocumentMetricsResponse,
    DocumentResponse,
    ExtractedDataResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_session)])


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
def get_document_metrics(
    use_case: GetDocumentMetrics = Depends(get_document_metrics_use_case),
) -> DocumentMetricsResponse:
    return DocumentMetricsResponse.model_validate(use_case.execute(), from_attributes=True)


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
    use_case=Depends(get_approve_document_use_case),
) -> DocumentResponse:
    """Reads the document, signs off on the result, and rebuilds what changed.

    One endpoint because it is one button. A document reaches the review screen
    precisely when the pipeline could make nothing of it, so approving without
    extracting would sign off on an empty result.
    """
    approved_by = payload.approved_by if payload is not None else None
    try:
        approved = use_case.execute(
            ApproveDocumentInput(document_id=document_id, approved_by=approved_by)
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentNotExtractable as exc:
        # 422, not 400: the request is well formed and the caller is entitled
        # to make it — nothing could be read from the file itself.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DocumentResponse.model_validate(approved.document, from_attributes=True)


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(
    document_id: str,
    use_case=Depends(get_reprocess_document_use_case),
) -> DocumentResponse:
    """Reads this one document's file again, whatever state it is in.

    The folder import refuses to touch an APPROVED document, on purpose: a
    sync must not undo a person's review as a side effect. This endpoint is
    the deliberate act that may, named per document — it is what a preparer
    needs after configuring or correcting the type this document belongs to.

    The approval does not survive it: the document comes back PROCESSED and
    has to be approved again, because the figures on it are now ones nobody
    has looked at.

    A reading that fails comes back 200 with a FAILED document rather than an
    error status. Unlike approving — which declines and leaves everything as
    it was — the reread has already replaced what the document held, so the
    failure is the document's new state, and the caller needs it to show why.
    """
    try:
        reprocessed = use_case.execute(ReprocessDocumentInput(document_id=document_id))
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DocumentResponse.model_validate(reprocessed.document, from_attributes=True)
