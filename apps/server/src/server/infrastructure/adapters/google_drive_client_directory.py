import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from server.domain.ports import ClientFolder

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_FOLDER_MIME = "application/vnd.google-apps.folder"
_PAGE_SIZE = 100

_logger = logging.getLogger(__name__)


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
        _logger.debug("Listing client folders in %s with query: %s", self._root_folder_id, query)

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
                        # Without these a folder living in a Shared Drive is
                        # silently skipped: the call succeeds and returns
                        # nothing, which is indistinguishable from an empty
                        # folder.
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                page = [ClientFolder(id=f["id"], name=f["name"]) for f in response.get("files", [])]
                _logger.debug(
                    "Drive returned %d subfolder(s): %s",
                    len(page),
                    [f.name for f in page],
                )
                folders.extend(page)

                page_token = response.get("nextPageToken")
                if not page_token:
                    if not folders:
                        # The API answers 200 with an empty list when the folder
                        # is not shared with the service account, so say so.
                        _logger.warning(
                            "No subfolders found in Drive folder %s. Check that the id is "
                            "right and that the folder is shared with the service account.",
                            self._root_folder_id,
                        )
                    _logger.info("Found %d client folder(s) in Drive", len(folders))
                    return folders
        except HttpError as exc:
            _logger.error("Drive rejected the folder listing: %s", exc)
            raise DriveDirectoryError("Could not list the Drive clients folder") from exc
