import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from server.application.use_cases import ProcessDriveChangeNotification, SubscribeDriveWebhook
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_process_drive_change_notification_use_case,
    get_settings,
    get_subscribe_drive_webhook_use_case,
)
from server.infrastructure.api.schemas import DriveWatchChannelResponse
from server.infrastructure.config.settings import Settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/drive", status_code=200)
def handle_drive_webhook(
    x_goog_channel_id: str | None = Header(default=None),
    x_goog_channel_token: str | None = Header(default=None),
    x_goog_resource_state: str | None = Header(default=None),
    use_case: ProcessDriveChangeNotification = Depends(
        get_process_drive_change_notification_use_case
    ),
    settings: Settings = Depends(get_settings),
) -> Response:
    if (
        not settings.google_drive_webhook_secret
        or not x_goog_channel_token
        or not secrets.compare_digest(x_goog_channel_token, settings.google_drive_webhook_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if x_goog_channel_id is None:
        raise HTTPException(status_code=400, detail="Missing channel id")

    use_case.execute(channel_id=x_goog_channel_id, resource_state=x_goog_resource_state or "")
    return Response(status_code=200)


@router.post(
    "/drive/subscribe",
    response_model=DriveWatchChannelResponse,
    status_code=201,
    dependencies=[Depends(require_session)],
)
def subscribe_drive_webhook(
    folder_id: str,
    client_id: str,
    use_case: SubscribeDriveWebhook = Depends(get_subscribe_drive_webhook_use_case),
    settings: Settings = Depends(get_settings),
) -> DriveWatchChannelResponse:
    if not settings.google_drive_webhook_secret:
        raise HTTPException(status_code=500, detail="Drive webhook secret is not configured")

    channel = use_case.execute(
        folder_id=folder_id,
        client_id=client_id,
        webhook_url=f"{settings.server_public_url}/webhooks/drive",
        token=settings.google_drive_webhook_secret,
    )
    return DriveWatchChannelResponse.model_validate(channel, from_attributes=True)
