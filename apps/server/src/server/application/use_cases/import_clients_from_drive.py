import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import Client
from server.domain.ports import ClientDirectory, ClientRepository


@dataclass(frozen=True, slots=True)
class ImportResult:
    created: list[Client]
    renamed: list[Client]
    unchanged: int


class ImportClientsFromDrive:
    """Makes the client list mirror the subfolders of the Drive clients folder.

    Folders are matched by their Drive id, not by name, so renaming a folder
    updates the client instead of creating a second one. Nothing is ever deleted:
    a folder disappearing from Drive must not take its documents' client with it.
    """

    def __init__(self, directory: ClientDirectory, clients: ClientRepository) -> None:
        self._directory = directory
        self._clients = clients

    def execute(self) -> ImportResult:
        existing = {c.drive_folder_id: c for c in self._clients.list_all() if c.drive_folder_id}

        created: list[Client] = []
        renamed: list[Client] = []
        unchanged = 0

        for folder in self._directory.list_client_folders():
            current = existing.get(folder.id)
            drive_folder_url = f"https://drive.google.com/drive/folders/{folder.id}"

            if current is None:
                client = Client(
                    id=str(uuid.uuid4()),
                    name=folder.name,
                    tax_id=None,
                    email=None,
                    created_at=datetime.now(UTC),
                    drive_folder_id=folder.id,
                    drive_folder_url=drive_folder_url,
                )
                self._clients.save(client)
                created.append(client)
            elif current.name != folder.name:
                # Keep whatever was filled in on top of the import.
                client = Client(
                    id=current.id,
                    name=folder.name,
                    tax_id=current.tax_id,
                    email=current.email,
                    created_at=current.created_at,
                    drive_folder_id=current.drive_folder_id,
                    drive_folder_url=current.drive_folder_url or drive_folder_url,
                )
                self._clients.save(client)
                renamed.append(client)
            elif current.drive_folder_url is None:
                # Backfills clients imported before drive_folder_url existed.
                client = Client(
                    id=current.id,
                    name=current.name,
                    tax_id=current.tax_id,
                    email=current.email,
                    created_at=current.created_at,
                    drive_folder_id=current.drive_folder_id,
                    drive_folder_url=drive_folder_url,
                )
                self._clients.save(client)
                unchanged += 1
            else:
                unchanged += 1

        return ImportResult(created=created, renamed=renamed, unchanged=unchanged)
