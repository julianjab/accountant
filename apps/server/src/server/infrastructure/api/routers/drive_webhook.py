import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response

from server.application.use_cases import ProcessDriveChangeNotification, SubscribeDriveWebhook
from server.domain.ports import DriveWatchChannelRepository
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_drive_watch_channel_repository,
    get_process_drive_change_notification_use_case,
    get_settings,
    get_subscribe_drive_webhook_use_case,
)
from server.infrastructure.api.schemas import DocumentResponse, DriveWatchChannelResponse
from server.infrastructure.config.settings import Settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/drive", status_code=200)
def handle_drive_webhook(
    background_tasks: BackgroundTasks,
    x_goog_channel_id: str | None = Header(default=None),
    x_goog_channel_token: str | None = Header(default=None),
    x_goog_resource_state: str | None = Header(default=None),
    use_case: ProcessDriveChangeNotification = Depends(
        get_process_drive_change_notification_use_case
    ),
    channels: DriveWatchChannelRepository = Depends(get_drive_watch_channel_repository),
) -> Response:
    if x_goog_channel_id is None:
        raise HTTPException(status_code=400, detail="Missing channel id")

    # The token is per-channel (see SubscribeDriveWebhook), so it can only be
    # validated once the channel it claims to belong to is known.
    channel = channels.get_by_channel_id(x_goog_channel_id)
    if (
        channel is None
        or not x_goog_channel_token
        or not secrets.compare_digest(x_goog_channel_token, channel.token)
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    # Drive expects an ack within seconds; classification+OCR can take much
    # longer, and a slow response only earns a redundant retry of the same
    # notification. Acknowledge immediately and do the work after responding.
    background_tasks.add_task(
        use_case.execute, channel_id=x_goog_channel_id, resource_state=x_goog_resource_state or ""
    )
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
    channel = use_case.execute(
        folder_id=folder_id,
        client_id=client_id,
        webhook_url=f"{settings.server_public_url}/webhooks/drive",
    )
    return DriveWatchChannelResponse.model_validate(channel, from_attributes=True)


@router.post(
    "/drive/{channel_id}/retry",
    response_model=list[DocumentResponse],
    dependencies=[Depends(require_session)],
)
def retry_drive_channel(
    channel_id: str,
    use_case: ProcessDriveChangeNotification = Depends(
        get_process_drive_change_notification_use_case
    ),
    channels: DriveWatchChannelRepository = Depends(get_drive_watch_channel_repository),
) -> list[DocumentResponse]:
    # A file that keeps failing holds the channel's cursor back on purpose
    # (see ProcessDriveChangeNotification), so it is retried automatically
    # the next time Drive sends a notification for that channel. But if that
    # failed file was the last real change, nothing ever triggers again on
    # its own; calling this manually (from a cron, a future scheduler, or an
    # admin action) re-runs the exact same processing path against the
    # channel's currently-persisted page_token without waiting for one.
    if channels.get_by_channel_id(channel_id) is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    documents = use_case.execute(channel_id=channel_id, resource_state="")
    return [DocumentResponse.model_validate(d, from_attributes=True) for d in documents]
