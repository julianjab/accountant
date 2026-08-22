from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DocumentContent:
    data: bytes
    mime_type: str
    file_name: str


class DocumentStorage(Protocol):
    """Port to the document storage provider (e.g. Google Drive)."""

    def download(self, file_reference: str) -> DocumentContent: ...
