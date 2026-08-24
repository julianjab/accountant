from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import (
    ApproveDocument,
    ApproveDocumentInput,
    DocumentAlreadyApproved,
    DocumentNotApprovable,
    DocumentNotFound,
    DocumentNotRecognized,
    GetDocumentMetrics,
    GetExtractedData,
    RecognizeDocumentSourceInput,
)
from server.domain.entities import DocumentStatus
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_approve_document_use_case,
    get_document_metrics_use_case,
    get_document_repository,
    get_extracted_data_use_case,
    get_recognize_document_source_use_case,
    get_source_parsers,
)
from server.infrastructure.api.schemas import (
    DocumentApproveRequest,
    DocumentMetricsResponse,
    DocumentRecognizeRequest,
    DocumentResponse,
    DocumentSourceResponse,
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


# Declared before "/{document_id}", or FastAPI would match "sources" as a
# document id and answer 404 for every request to this.
@router.get("/sources", response_model=list[DocumentSourceResponse])
def list_document_sources(parsers=Depends(get_source_parsers)) -> list[DocumentSourceResponse]:
    """The formats a person can declare a document to be.

    Offered because the classifier cannot propose these: they are read by a
    parser rather than configured as document types, so a file of one of these
    formats always fails classification and has to be named by hand.
    """
    return [
        DocumentSourceResponse(
            id=source.id, label=source.label, media_types=sorted(source.media_types)
        )
        for source in parsers.available()
    ]


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


@router.post("/{document_id}/recognize", response_model=DocumentResponse)
def recognize_document_source(
    document_id: str,
    payload: DocumentRecognizeRequest,
    use_case=Depends(get_recognize_document_source_use_case),
) -> DocumentResponse:
    try:
        recognized = use_case.execute(
            RecognizeDocumentSourceInput(document_id=document_id, source_id=payload.source_id)
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentAlreadyApproved as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DocumentNotRecognized as exc:
        # 422, not 400: the request is well formed and the caller is entitled
        # to make it — the file simply turned out not to be what they said.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DocumentResponse.model_validate(recognized.document, from_attributes=True)
