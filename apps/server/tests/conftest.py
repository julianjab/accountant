"""Keeps the test suite off real infrastructure.

`Settings` reads `.env`, and a developer's `.env` sets
`ACCOUNTANT_FIRESTORE_PROJECT` so the server can talk to the real database.
Without this file that setting reaches the tests too: `get_firestore()` returns
a live client, every repository fixture becomes a Firestore-backed one, and the
suite reads and writes the actual clients' tax data — asserting counts against
whatever happens to be in production, and leaving its own fixtures behind.

Clearing the variable before anything imports `Settings` puts every repository
back on its in-memory adapter, which is what the tests are written against.
"""

import os

import pytest

# Set at import time, not in a fixture: pytest imports this module during
# collection, before any test module can construct a cached Settings.
os.environ["ACCOUNTANT_FIRESTORE_PROJECT"] = ""


@pytest.fixture(autouse=True, scope="session")
def _refuse_real_firestore():
    """Fails the run rather than letting a test touch the real database.

    The failure mode this guards against is silent: a live client produces
    tests that pass locally, mutate production data, and fail unpredictably
    depending on what is already stored.
    """
    from server.infrastructure.api.deps import get_firestore, get_settings

    get_settings.cache_clear()
    get_firestore.cache_clear()
    assert get_firestore() is None, (
        "Tests are configured to reach a real Firestore project. "
        "ACCOUNTANT_FIRESTORE_PROJECT must be empty during tests."
    )
    yield
    get_settings.cache_clear()
    get_firestore.cache_clear()
