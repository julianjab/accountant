import threading
from datetime import UTC, datetime

from server.domain.entities import Document, DocumentStatus
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryDriveFileClaimRepository,
)


def test_try_claim_succeeds_only_once():
    repo = InMemoryDriveFileClaimRepository()

    assert repo.try_claim("file-1") is True
    assert repo.try_claim("file-1") is False


def test_release_allows_claiming_again():
    repo = InMemoryDriveFileClaimRepository()
    repo.try_claim("file-1")

    repo.release("file-1")

    assert repo.try_claim("file-1") is True


def test_release_of_an_unclaimed_file_is_a_no_op():
    repo = InMemoryDriveFileClaimRepository()

    repo.release("never-claimed")

    assert repo.try_claim("never-claimed") is True


def test_try_claim_is_safe_under_concurrent_threads():
    # Sync route handlers (and the BackgroundTasks callbacks scheduled from
    # them) run in FastAPI's threadpool, not the event loop, so two
    # notifications for the same file can genuinely race here.
    repo = InMemoryDriveFileClaimRepository()
    results: list[bool] = []
    lock = threading.Lock()

    def claim() -> None:
        result = repo.try_claim("file-1")
        with lock:
            results.append(result)

    threads = [threading.Thread(target=claim) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 1
    assert results.count(False) == 19


def test_record_failure_increments_and_clear_failures_resets():
    repo = InMemoryDriveFileClaimRepository()

    assert repo.record_failure("file-1") == 1
    assert repo.record_failure("file-1") == 2

    repo.clear_failures("file-1")

    assert repo.record_failure("file-1") == 1


def test_get_by_drive_file_id_and_client_is_scoped_to_the_client():
    repo = InMemoryDocumentRepository()
    mine = Document(
        id="d1",
        client_id="c1",
        document_type_id=None,
        drive_file_id="f1",
        file_name="a.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        error=None,
        created_at=datetime.now(UTC),
    )
    other_clients_copy = Document(
        id="d2",
        client_id="c2",
        document_type_id=None,
        drive_file_id="f1",
        file_name="a.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        error=None,
        created_at=datetime.now(UTC),
    )
    repo.save(mine)
    repo.save(other_clients_copy)

    assert repo.get_by_drive_file_id_and_client("f1", "c1") == mine
    assert repo.get_by_drive_file_id_and_client("f1", "c2") == other_clients_copy
    assert repo.get_by_drive_file_id_and_client("f1", "c3") is None
