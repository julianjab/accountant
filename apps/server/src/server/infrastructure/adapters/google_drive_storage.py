import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from server.domain.ports import DocumentContent

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveStorage:
    """DocumentStorage adapter backed by the Google Drive API."""

    def __init__(self, service_account_file: str) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=_SCOPES
        )
        self._drive = build("drive", "v3", credentials=credentials)

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
