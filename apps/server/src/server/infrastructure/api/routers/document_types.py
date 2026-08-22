from fastapi import APIRouter, Depends, File, Form, UploadFile

from server.application.use_cases import DefineDocumentType, DefineDocumentTypeInput
from server.domain.ports import DocumentContent
from server.infrastructure.api.deps import get_define_document_type_use_case
from server.infrastructure.api.schemas import DocumentTypeResponse

router = APIRouter(prefix="/document-types", tags=["document-types"])


@router.post("", response_model=DocumentTypeResponse, status_code=201)
async def create_document_type(
    name: str = Form(...),
    description: str = Form(...),
    sample_file: UploadFile = File(...),
    use_case: DefineDocumentType = Depends(get_define_document_type_use_case),
) -> DocumentTypeResponse:
    sample_document = DocumentContent(
        data=await sample_file.read(),
        mime_type=sample_file.content_type or "application/octet-stream",
        file_name=sample_file.filename or "sample",
    )
    document_type = use_case.execute(
        DefineDocumentTypeInput(name=name, description=description, sample_document=sample_document)
    )
    return DocumentTypeResponse.model_validate(document_type, from_attributes=True)
