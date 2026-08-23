from typing import Protocol

from server.domain.entities import DriveWatchChannel


class DriveWatcher(Protocol):
    def watch(self, folder_id: str, webhook_url: str, token: str) -> DriveWatchChannel: ...
