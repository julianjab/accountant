from server.application.use_cases import RegisterClient, RegisterClientInput
from server.infrastructure.adapters.in_memory_repositories import InMemoryClientRepository


def test_register_client_persists_and_returns_client() -> None:
    clients = InMemoryClientRepository()
    use_case = RegisterClient(clients)

    client = use_case.execute(
        RegisterClientInput(
            name="Jane Doe",
            tax_id="123456789",
            email="jane@example.com",
            drive_folder_url="https://drive.google.com/drive/folders/abc",
        )
    )

    assert clients.get(client.id) == client
    assert client.name == "Jane Doe"
    assert client.drive_folder_url == "https://drive.google.com/drive/folders/abc"


def test_register_client_defaults_drive_folder_url_to_none() -> None:
    clients = InMemoryClientRepository()
    use_case = RegisterClient(clients)

    client = use_case.execute(RegisterClientInput(name="Jane Doe", tax_id="123456789", email=None))

    assert client.drive_folder_url is None
    assert client.spreadsheet_url is None


def test_register_client_persists_spreadsheet_url() -> None:
    clients = InMemoryClientRepository()
    use_case = RegisterClient(clients)

    client = use_case.execute(
        RegisterClientInput(
            name="Jane Doe",
            tax_id="123456789",
            email="jane@example.com",
            spreadsheet_url="https://docs.google.com/spreadsheets/d/abc",
        )
    )

    assert client.spreadsheet_url == "https://docs.google.com/spreadsheets/d/abc"
