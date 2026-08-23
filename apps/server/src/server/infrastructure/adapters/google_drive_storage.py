import io
from datetime import UTC, datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from server.domain.entities import DriveChangedFile, DriveChangesPage, DriveWatchRegistration
from server.domain.ports import DocumentContent

# Drive's documented default channel TTL when a watch response omits "expiration".
_DEFAULT_CHANNEL_TTL = timedelta(days=7)

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _build_drive_client(service_account_file: str):
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=_SCOPES
    )
    return build("drive", "v3", credentials=credentials)


class GoogleDriveStorage:
    """DocumentStorage adapter backed by the Google Drive API."""

    def __init__(self, service_account_file: str) -> None:
        self._drive = _build_drive_client(service_account_file)

    def download(self, file_reference: str) -> DocumentContent:
        metadata = self._drive.files().get(fileId=file_reference, fields="name,mimeType").execute()

        buffer = io.BytesIO()
        request = self._drive.files().get_media(fileId=file_reference)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return DocumentContent(
            data=buffer.getvalue(),
            mime_type=metadata["mimeType"],
            file_name=metadata["name"],
        )


class GoogleDriveWatcher:
    """DriveWatcher/DriveChangeReader adapter built on the Drive Changes API.

    ``changes().watch()`` (not ``files().watch()``) is what a folder's *contents*
    require: watching the folder resource itself only reports changes to the
    folder's own metadata, not to files created inside it.
    """

    def __init__(self, service_account_file: str) -> None:
        self._drive = _build_drive_client(service_account_file)

    def get_start_page_token(self) -> str:
        return self._drive.changes().getStartPageToken().execute()["startPageToken"]

    def watch(
        self,
        channel_id: str,
        folder_id: str,
        webhook_url: str,
        token: str,
        start_page_token: str,
    ) -> DriveWatchRegistration:
        response = (
            self._drive.changes()
            .watch(
                pageToken=start_page_token,
                body={
                    "id": channel_id,
                    "type": "web_hook",
                    "address": webhook_url,
                    "token": token,
                },
            )
            .execute()
        )

        expiration = response.get("expiration")
        expires_at = (
            datetime.fromtimestamp(int(expiration) / 1000, tz=UTC)
            if expiration
            else datetime.now(UTC) + _DEFAULT_CHANNEL_TTL
        )
        return DriveWatchRegistration(resource_id=response["resourceId"], expires_at=expires_at)

    def list_changes(self, page_token: str) -> DriveChangesPage:
        response = (
            self._drive.changes()
            .list(
                pageToken=page_token,
                fields="nextPageToken,newStartPageToken,changes(fileId,removed,file(name,mimeType,parents,trashed))",
            )
            .execute()
        )

        files = []
        for change in response.get("changes", []):
            file = change.get("file")
            if change.get("removed") or file is None:
                continue
            files.append(
                DriveChangedFile(
                    id=change["fileId"],
                    name=file["name"],
                    mime_type=file["mimeType"],
                    parents=file.get("parents", []),
                    trashed=file.get("trashed", False),
                )
            )

        next_page_token = response.get("nextPageToken") or response.get("newStartPageToken")
        return DriveChangesPage(files=files, next_page_token=next_page_token)
