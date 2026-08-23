import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from server.application.use_cases import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
    SubscribeDriveWebhook,
)
from server.infrastructure.api.deps import (
    get_process_uploaded_document_use_case,
    get_settings,
    get_subscribe_drive_webhook_use_case,
)
from server.infrastructure.api.schemas import (
    DocumentResponse,
    DriveWatchChannelResponse,
    DriveWebhookPayload,
)
from server.infrastructure.config.settings import Settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/drive", response_model=DocumentResponse, status_code=201)
def handle_drive_webhook(
    payload: DriveWebhookPayload,
    x_goog_channel_token: str | None = Header(default=None),
    use_case: ProcessUploadedDocument = Depends(get_process_uploaded_document_use_case),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    if (
        not settings.google_drive_webhook_secret
        or not x_goog_channel_token
        or not secrets.compare_digest(x_goog_channel_token, settings.google_drive_webhook_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    document = use_case.execute(
        ProcessUploadedDocumentInput(
            client_id=payload.client_id,
            drive_file_id=payload.drive_file_id,
            file_reference=payload.file_reference,
        )
    )
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.post("/drive/subscribe", response_model=DriveWatchChannelResponse, status_code=201)
def subscribe_drive_webhook(
    folder_id: str,
    use_case: SubscribeDriveWebhook = Depends(get_subscribe_drive_webhook_use_case),
    settings: Settings = Depends(get_settings),
) -> DriveWatchChannelResponse:
    if not settings.google_drive_webhook_secret:
        raise HTTPException(status_code=500, detail="Drive webhook secret is not configured")

    channel = use_case.execute(
        folder_id=folder_id,
        webhook_url=f"{settings.server_public_url}/webhooks/drive",
        token=settings.google_drive_webhook_secret,
    )
    return DriveWatchChannelResponse.model_validate(channel, from_attributes=True)
