import io
import uuid
from datetime import UTC, datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from server.domain.entities import DriveWatchChannel
from server.domain.ports import DocumentContent

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
    """DriveWatcher adapter that registers a push-notification channel via files().watch()."""

    def __init__(self, service_account_file: str) -> None:
        self._drive = _build_drive_client(service_account_file)

    def watch(self, folder_id: str, webhook_url: str, token: str) -> DriveWatchChannel:
        channel_id = str(uuid.uuid4())
        response = (
            self._drive.files()
            .watch(
                fileId=folder_id,
                body={
                    "id": channel_id,
                    "type": "web_hook",
                    "address": webhook_url,
                    "token": token,
                },
            )
            .execute()
        )

        return DriveWatchChannel(
            id=channel_id,
            resource_id=response["resourceId"],
            folder_id=folder_id,
            expires_at=datetime.fromtimestamp(int(response["expiration"]) / 1000, tz=UTC),
        )
