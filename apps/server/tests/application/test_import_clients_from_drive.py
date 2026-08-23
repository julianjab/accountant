from datetime import UTC, datetime

from server.application.use_cases import ImportClientsFromDrive
from server.domain.entities import Client
from server.domain.ports import ClientFolder
from server.infrastructure.adapters.in_memory_repositories import InMemoryClientRepository


class FakeDirectory:
    def __init__(self, folders: list[ClientFolder]) -> None:
        self._folders = folders

    def list_client_folders(self) -> list[ClientFolder]:
        return self._folders


def test_a_new_folder_becomes_a_client():
    clients = InMemoryClientRepository()
    directory = FakeDirectory([ClientFolder(id="f1", name="Acme SAS")])

    result = ImportClientsFromDrive(directory, clients).execute()

    assert [c.name for c in result.created] == ["Acme SAS"]
    saved = clients.list_all()[0]
    assert saved.drive_folder_id == "f1"
    # A folder carries no tax id; it is filled in later.
    assert saved.tax_id is None


def test_importing_twice_does_not_duplicate():
    clients = InMemoryClientRepository()
    directory = FakeDirectory([ClientFolder(id="f1", name="Acme SAS")])
    use_case = ImportClientsFromDrive(directory, clients)

    use_case.execute()
    result = use_case.execute()

    assert result.created == []
    assert result.unchanged == 1
    assert len(clients.list_all()) == 1


def test_a_renamed_folder_updates_the_client_instead_of_creating_one():
    clients = InMemoryClientRepository()
    ImportClientsFromDrive(FakeDirectory([ClientFolder(id="f1", name="Acme")]), clients).execute()

    result = ImportClientsFromDrive(
        FakeDirectory([ClientFolder(id="f1", name="Acme SAS")]), clients
    ).execute()

    # Matching is by Drive id, so a rename must not fork the client.
    assert len(clients.list_all()) == 1
    assert [c.name for c in result.renamed] == ["Acme SAS"]
    assert clients.list_all()[0].name == "Acme SAS"


def test_a_rename_keeps_data_filled_in_on_top_of_the_import():
    clients = InMemoryClientRepository()
    clients.save(
        Client(
            id="c1",
            name="Acme",
            tax_id="900123456",
            email="a@acme.co",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            drive_folder_id="f1",
        )
    )

    ImportClientsFromDrive(
        FakeDirectory([ClientFolder(id="f1", name="Acme SAS")]), clients
    ).execute()

    saved = clients.get("c1")
    assert saved.name == "Acme SAS"
    assert saved.tax_id == "900123456"
    assert saved.email == "a@acme.co"
    assert saved.created_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_a_folder_disappearing_does_not_delete_its_client():
    clients = InMemoryClientRepository()
    ImportClientsFromDrive(FakeDirectory([ClientFolder(id="f1", name="Acme")]), clients).execute()

    ImportClientsFromDrive(FakeDirectory([]), clients).execute()

    # Deleting would orphan whatever documents already reference the client.
    assert len(clients.list_all()) == 1


def test_clients_created_by_hand_are_left_alone():
    clients = InMemoryClientRepository()
    clients.save(
        Client(
            id="manual",
            name="Typed in",
            tax_id="1",
            email=None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    result = ImportClientsFromDrive(
        FakeDirectory([ClientFolder(id="f1", name="Acme")]), clients
    ).execute()

    assert len(result.created) == 1
    assert clients.get("manual").name == "Typed in"
