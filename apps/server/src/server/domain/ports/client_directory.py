from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ClientFolder:
    id: str
    name: str


class ClientDirectory(Protocol):
    """Lists the folders that stand for clients.

    Separate from ``DocumentStorage``: that port is about reading a file's bytes,
    this one is about discovering who the clients are.
    """

    def list_client_folders(self) -> list[ClientFolder]: ...
