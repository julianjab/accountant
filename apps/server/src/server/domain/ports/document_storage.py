from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DocumentContent:
    data: bytes
    mime_type: str
    file_name: str


@dataclass(frozen=True, slots=True)
class StoredFile:
    """A file sitting in a client's folder, before anything has been read."""

    id: str
    name: str
    mime_type: str


class DocumentStorage(Protocol):
    """Port to the document storage provider (e.g. Google Drive)."""

    def download(self, file_reference: str) -> DocumentContent: ...

    def list_files(self, folder_reference: str) -> list[StoredFile]:
        """Every file currently in a folder.

        Needed because change notifications only ever report what happens
        after a subscription starts. Whatever was already in the folder is
        invisible to that feed forever, so importing a client has to be able
        to look at the folder as it stands.
        """
        ...
