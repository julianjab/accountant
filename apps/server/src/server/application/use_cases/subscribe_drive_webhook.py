import secrets
import uuid

from server.domain.entities import DriveWatchChannel
from server.domain.ports import DriveWatchChannelRepository, DriveWatcher


class SubscribeDriveWebhook:
    """Registers a Drive push-notification channel so uploads trigger the webhook."""

    def __init__(self, watcher: DriveWatcher, channels: DriveWatchChannelRepository) -> None:
        self._watcher = watcher
        self._channels = channels

    def execute(self, folder_id: str, client_id: str, webhook_url: str) -> DriveWatchChannel:
        channel_id = str(uuid.uuid4())
        # Each channel gets its own shared secret rather than reusing one secret
        # across every subscription: a channel_id (which appears in the webhook
        # request itself, not secret) is otherwise all that gates which folder/
        # client a caller can trigger processing for.
        token = secrets.token_urlsafe(32)
        start_page_token = self._watcher.get_start_page_token()
        registration = self._watcher.watch(
            channel_id, folder_id, webhook_url, token, start_page_token
        )

        channel = DriveWatchChannel(
            id=channel_id,
            resource_id=registration.resource_id,
            folder_id=folder_id,
            client_id=client_id,
            token=token,
            page_token=start_page_token,
            expires_at=registration.expires_at,
        )
        self._channels.save(channel)
        return channel
