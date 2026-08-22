from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Client:
    id: str
    name: str
    tax_id: str
    email: str | None
    created_at: datetime
