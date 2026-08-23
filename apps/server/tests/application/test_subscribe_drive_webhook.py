from datetime import UTC, datetime

from server.application.use_cases import SubscribeDriveWebhook
from server.domain.entities import DriveWatchChannel


class FakeDriveWatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def watch(self, folder_id: str, webhook_url: str, token: str) -> DriveWatchChannel:
        self.calls.append((folder_id, webhook_url, token))
        return DriveWatchChannel(
            id="channel-id",
            resource_id="resource-id",
            folder_id=folder_id,
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_subscribe_drive_webhook_registers_a_channel_for_the_folder():
    watcher = FakeDriveWatcher()
    use_case = SubscribeDriveWebhook(watcher)

    channel = use_case.execute(
        folder_id="folder-1", webhook_url="https://example.com/webhooks/drive", token="secret"
    )

    assert channel.folder_id == "folder-1"
    assert channel.id == "channel-id"
    assert channel.resource_id == "resource-id"
    assert watcher.calls == [("folder-1", "https://example.com/webhooks/drive", "secret")]
