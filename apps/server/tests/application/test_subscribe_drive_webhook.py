from datetime import UTC, datetime

from server.application.use_cases import SubscribeDriveWebhook
from server.domain.entities import DriveWatchChannel, DriveWatchRegistration


class FakeDriveWatcher:
    def __init__(self) -> None:
        self.watch_calls: list[tuple[str, str, str, str, str]] = []

    def get_start_page_token(self) -> str:
        return "start-token"

    def watch(
        self,
        channel_id: str,
        folder_id: str,
        webhook_url: str,
        token: str,
        start_page_token: str,
    ) -> DriveWatchRegistration:
        self.watch_calls.append((channel_id, folder_id, webhook_url, token, start_page_token))
        return DriveWatchRegistration(
            resource_id="resource-id", expires_at=datetime(2026, 1, 1, tzinfo=UTC)
        )


class FakeDriveWatchChannelRepository:
    def __init__(self) -> None:
        self.saved: list[DriveWatchChannel] = []

    def save(self, channel: DriveWatchChannel) -> None:
        self.saved.append(channel)

    def get_by_channel_id(self, channel_id: str) -> DriveWatchChannel | None:
        return next((c for c in self.saved if c.id == channel_id), None)


def test_subscribe_drive_webhook_registers_and_persists_a_channel_for_the_folder():
    watcher = FakeDriveWatcher()
    channels = FakeDriveWatchChannelRepository()
    use_case = SubscribeDriveWebhook(watcher, channels)

    channel = use_case.execute(
        folder_id="folder-1",
        client_id="client-1",
        webhook_url="https://example.com/webhooks/drive",
        token="secret",
    )

    assert channel.folder_id == "folder-1"
    assert channel.client_id == "client-1"
    assert channel.resource_id == "resource-id"
    assert channel.page_token == "start-token"

    [call] = watcher.watch_calls
    assert call == (
        channel.id,
        "folder-1",
        "https://example.com/webhooks/drive",
        "secret",
        "start-token",
    )
    assert channels.saved == [channel]
