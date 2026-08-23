import threading

from server.infrastructure.adapters.in_memory_repositories import (
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
