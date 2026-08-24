"""Keeps the test suite off real infrastructure and off the developer's config.

`Settings` reads `.env`, so without this file the machine's own configuration
decides how the tests behave. That produced two separate failures already:
`ACCOUNTANT_FIRESTORE_PROJECT` made every repository fixture Firestore-backed,
so the suite read and wrote real clients' tax data and asserted counts against
whatever happened to be in production; and pointing the app at a tunnel set
`SESSION_COOKIE_SECURE`, after which the test client would not send a cookie
over http and the auth tests started returning 401.

Both have the same cause, so the fix is the cause and not the symptoms: tests
do not read `.env` at all. Every setting falls back to its declared default,
which is what the tests were written against, and the suite behaves the same on
any machine.
"""

import os

import dotenv
import pytest

from server.infrastructure.config.settings import Settings

# All three applied at import time, not in a fixture: pytest imports this module
# during collection, before any test module can import `main` or build a cached
# Settings.

# 1. Settings stops reading the file itself.
Settings.model_config["env_file"] = None

# 2. `main` calls load_dotenv() at import, which copies `.env` into the real
#    environment — where it outranks anything above. Neutered for the suite.
dotenv.load_dotenv = lambda *args, **kwargs: False

# 3. Anything already exported before pytest started, or loaded by an earlier
#    import, is dropped so the declared defaults are what the tests see.
for name in [key for key in os.environ if key.startswith("ACCOUNTANT_")]:
    del os.environ[name]


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
