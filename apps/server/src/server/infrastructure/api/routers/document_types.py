from fastapi import APIRouter, Depends, File, Form, UploadFile

from server.application.use_cases import DefineDocumentType, DefineDocumentTypeInput
from server.domain.ports import DocumentContent
from server.infrastructure.api.deps import (
    get_define_document_type_use_case,
    get_document_type_repository,
)
from server.infrastructure.api.schemas import DocumentTypeResponse

router = APIRouter(prefix="/document-types", tags=["document-types"])


@router.get("", response_model=list[DocumentTypeResponse])
def list_document_types(
    active_only: bool = True,
    document_types=Depends(get_document_type_repository),
) -> list[DocumentTypeResponse]:
    items = document_types.list_active() if active_only else document_types.list_all()
    return [DocumentTypeResponse.model_validate(t, from_attributes=True) for t in items]


@router.post("", response_model=DocumentTypeResponse, status_code=201)
def create_document_type(
    name: str = Form(...),
    description: str = Form(...),
    sample_file: UploadFile = File(...),
    use_case: DefineDocumentType = Depends(get_define_document_type_use_case),
) -> DocumentTypeResponse:
    # Sync on purpose: this calls a blocking AIProvider (httpx.Client) — a
    # `def` handler runs in FastAPI's threadpool instead of on the event
    # loop, unlike `async def`, which would stall every other request for
    # as long as the Claude call takes.
    sample_document = DocumentContent(
        data=sample_file.file.read(),
        mime_type=sample_file.content_type or "application/octet-stream",
        file_name=sample_file.filename or "sample",
    )
    document_type = use_case.execute(
        DefineDocumentTypeInput(name=name, description=description, sample_document=sample_document)
    )
    return DocumentTypeResponse.model_validate(document_type, from_attributes=True)
