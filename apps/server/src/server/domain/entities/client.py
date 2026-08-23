from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Client:
    id: str
    name: str
    # Optional because a client can originate from a Drive folder, which carries
    # a name but no tax id; it is filled in later.
    tax_id: str | None
    email: str | None
    created_at: datetime
    # The Drive folder this client was imported from, and the link that lets an
    # incoming document be attributed to a client by where it landed.
    drive_folder_id: str | None = None
    drive_folder_url: str | None = None
    spreadsheet_url: str | None = None
