from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from server.domain.ports import ClientFolder

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_FOLDER_MIME = "application/vnd.google-apps.folder"
_PAGE_SIZE = 100


class DriveDirectoryError(Exception):
    """The clients folder could not be listed."""


class GoogleDriveClientDirectory:
    """ClientDirectory adapter: each subfolder of a root folder is a client.

    Uses the service account, so the root folder must be shared with it — the
    same arrangement the document webhook already relies on.
    """

    def __init__(self, service_account_file: str, root_folder_id: str) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=_SCOPES
        )
        self._drive = build("drive", "v3", credentials=credentials)
        self._root_folder_id = root_folder_id

    def list_client_folders(self) -> list[ClientFolder]:
        if not self._root_folder_id:
            raise DriveDirectoryError("No Drive clients folder is configured")

        query = (
            f"'{self._root_folder_id}' in parents "
            f"and mimeType = '{_FOLDER_MIME}' and trashed = false"
        )

        folders: list[ClientFolder] = []
        page_token: str | None = None
        try:
            while True:
                response = (
                    self._drive.files()
                    .list(
                        q=query,
                        fields="nextPageToken, files(id, name)",
                        pageSize=_PAGE_SIZE,
                        pageToken=page_token,
                    )
                    .execute()
                )
                folders.extend(
                    ClientFolder(id=f["id"], name=f["name"]) for f in response.get("files", [])
                )
                page_token = response.get("nextPageToken")
                if not page_token:
                    return folders
        except HttpError as exc:
            raise DriveDirectoryError("Could not list the Drive clients folder") from exc
