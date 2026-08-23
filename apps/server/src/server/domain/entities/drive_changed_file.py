from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriveChangedFile:
    """A file the Drive Changes API reported as created/modified/removed."""

    id: str
    name: str
    mime_type: str
    parents: list[str]
    trashed: bool
