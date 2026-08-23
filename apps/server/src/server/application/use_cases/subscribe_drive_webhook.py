from server.domain.entities import DriveWatchChannel
from server.domain.ports import DriveWatcher


class SubscribeDriveWebhook:
    """Registers a Drive push-notification channel so uploads trigger the webhook."""

    def __init__(self, watcher: DriveWatcher) -> None:
        self._watcher = watcher

    def execute(self, folder_id: str, webhook_url: str, token: str) -> DriveWatchChannel:
        return self._watcher.watch(folder_id, webhook_url, token)
