from typing import Protocol

from server.domain.entities import DriveChangesPage, DriveWatchRegistration


class DriveWatcher(Protocol):
    def get_start_page_token(self) -> str: ...

    def watch(
        self,
        channel_id: str,
        folder_id: str,
        webhook_url: str,
        token: str,
        start_page_token: str,
    ) -> DriveWatchRegistration: ...


class DriveChangeReader(Protocol):
    def list_changes(self, page_token: str) -> DriveChangesPage: ...
