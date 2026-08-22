from server.application.use_cases import RegisterClient, RegisterClientInput
from server.infrastructure.adapters.in_memory_repositories import InMemoryClientRepository


def test_register_client_persists_and_returns_client() -> None:
    clients = InMemoryClientRepository()
    use_case = RegisterClient(clients)

    client = use_case.execute(
        RegisterClientInput(name="Jane Doe", tax_id="123456789", email="jane@example.com")
    )

    assert clients.get(client.id) == client
    assert client.name == "Jane Doe"
