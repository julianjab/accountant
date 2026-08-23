from dataclasses import dataclass

from server.domain.entities.drive_changed_file import DriveChangedFile


@dataclass(frozen=True, slots=True)
class DriveChangesPage:
    """A page of results from the Drive Changes API."""

    files: list[DriveChangedFile]
    next_page_token: str
