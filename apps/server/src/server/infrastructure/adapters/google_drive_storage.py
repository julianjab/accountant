import io
from datetime import UTC, datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from server.domain.entities import DriveChangedFile, DriveChangesPage, DriveWatchRegistration
from server.domain.ports import DocumentContent, StoredFile

# Drive's documented default channel TTL when a watch response omits "expiration".
_DEFAULT_CHANNEL_TTL = timedelta(days=7)

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
_PAGE_SIZE = 100


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
        metadata = (
            self._drive.files()
            .get(fileId=file_reference, fields="name,mimeType", supportsAllDrives=True)
            .execute()
        )

        buffer = io.BytesIO()
        request = self._drive.files().get_media(fileId=file_reference, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return DocumentContent(
            data=buffer.getvalue(),
            mime_type=metadata["mimeType"],
            file_name=metadata["name"],
        )

    def list_files(self, folder_reference: str) -> list[StoredFile]:
        files: list[StoredFile] = []
        page_token: str | None = None
        while True:
            response = (
                self._drive.files()
                .list(
                    q=f"'{folder_reference}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    # A client folder can sit in a shared drive; without these
                    # the listing silently comes back empty rather than failing.
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageSize=_PAGE_SIZE,
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(
                StoredFile(id=f["id"], name=f["name"], mime_type=f["mimeType"])
                for f in response.get("files", [])
                # Subfolders are not documents. Recursing into them is a
                # separate decision, and one that would change what a client's
                # folder means.
                if f["mimeType"] != _FOLDER_MIME_TYPE
            )
            page_token = response.get("nextPageToken")
            if not page_token:
                return files


class GoogleDriveWatcher:
    """DriveWatcher/DriveChangeReader adapter built on the Drive Changes API.

    ``changes().watch()`` (not ``files().watch()``) is what a folder's *contents*
    require: watching the folder resource itself only reports changes to the
    folder's own metadata, not to files created inside it.
    """

    def __init__(self, service_account_file: str) -> None:
        self._drive = _build_drive_client(service_account_file)

    def get_start_page_token(self) -> str:
        return (
            self._drive.changes()
            .getStartPageToken(supportsAllDrives=True)
            .execute()["startPageToken"]
        )

    def watch(
        self,
        channel_id: str,
        folder_id: str,
        webhook_url: str,
        token: str,
        start_page_token: str,
    ) -> DriveWatchRegistration:
        # supportsAllDrives/includeItemsFromAllDrives: without them, changes in a
        # folder that lives on a Shared Drive (the common case when a folder is
        # shared with a service account) never surface, with no error at all.
        response = (
            self._drive.changes()
            .watch(
                pageToken=start_page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
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
        # Drive paginates changes(); a caller that stops at the first page and
        # persists its "nextPageToken" as the new cursor silently drops every
        # change past the first page, since Drive never re-notifies for changes
        # it already reported. Loop until the API hands back "newStartPageToken",
        # which only appears on the final page and is the one safe cursor to persist.
        files = []
        next_page_token = page_token
        while True:
            response = (
                self._drive.changes()
                .list(
                    pageToken=next_page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    fields=(
                        "nextPageToken,newStartPageToken,"
                        "changes(fileId,removed,file(name,mimeType,parents,trashed))"
                    ),
                )
                .execute()
            )

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

            new_start_page_token = response.get("newStartPageToken")
            if new_start_page_token:
                return DriveChangesPage(files=files, next_page_token=new_start_page_token)
            next_page_token = response["nextPageToken"]
