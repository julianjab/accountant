import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import Client
from server.domain.ports import ClientRepository


@dataclass(frozen=True, slots=True)
class RegisterClientInput:
    name: str
    tax_id: str | None
    email: str | None


class RegisterClient:
    def __init__(self, clients: ClientRepository) -> None:
        self._clients = clients

    def execute(self, data: RegisterClientInput) -> Client:
        client = Client(
            id=str(uuid.uuid4()),
            name=data.name,
            tax_id=data.tax_id,
            email=data.email,
            created_at=datetime.now(UTC),
        )
        self._clients.save(client)
        return client
