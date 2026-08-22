from fastapi import APIRouter, Depends

from server.application.use_cases import ProcessUploadedDocument, ProcessUploadedDocumentInput
from server.infrastructure.api.deps import get_process_uploaded_document_use_case
from server.infrastructure.api.schemas import DocumentResponse, DriveWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/drive", response_model=DocumentResponse, status_code=201)
def handle_drive_webhook(
    payload: DriveWebhookPayload,
    use_case: ProcessUploadedDocument = Depends(get_process_uploaded_document_use_case),
) -> DocumentResponse:
    document = use_case.execute(
        ProcessUploadedDocumentInput(
            client_id=payload.client_id,
            drive_file_id=payload.drive_file_id,
            file_reference=payload.file_reference,
        )
    )
    return DocumentResponse.model_validate(document, from_attributes=True)
