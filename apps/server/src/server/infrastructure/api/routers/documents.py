from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import GetExtractedData
from server.infrastructure.api.deps import get_document_repository, get_extracted_data_use_case
from server.infrastructure.api.schemas import DocumentResponse, ExtractedDataResponse

router = APIRouter(prefix="/documents", tags=["documents"])


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
