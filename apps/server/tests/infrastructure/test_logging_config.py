import logging
import logging.handlers

from server.infrastructure.config.logging import configure_logging
from server.infrastructure.config.settings import Settings


def test_the_level_comes_from_configuration():
    configure_logging(Settings(log_level="debug"))

    # Lowercase must work: it is typed into a .env by hand.
    assert logging.getLogger("server.anything").getEffectiveLevel() == logging.DEBUG


def test_access_logs_stay_at_info_so_debug_does_not_drown_in_them():
    configure_logging(Settings(log_level="DEBUG"))

    assert logging.getLogger("uvicorn.access").getEffectiveLevel() == logging.INFO


def test_logs_go_to_stderr_when_no_file_is_configured():
    configure_logging(Settings(log_level="INFO"))

    handler = logging.getLogger("server").handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert not isinstance(handler, logging.FileHandler)


def test_a_configured_file_gets_a_rotating_handler(tmp_path):
    log_file = tmp_path / "server.log"

    configure_logging(Settings(log_level="INFO", log_file=str(log_file)))
    logging.getLogger("server.test").info("hello")

    handler = logging.getLogger("server").handlers[0]
    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    assert "hello" in log_file.read_text()


def test_the_json_format_is_selectable(tmp_path):
    log_file = tmp_path / "server.log"

    configure_logging(Settings(log_level="INFO", log_file=str(log_file), log_format="json"))
    logging.getLogger("server.test").warning("something happened")

    line = log_file.read_text()
    assert '"level": "WARNING"' in line
    assert '"message": "something happened"' in line


def teardown_module():
    # Leave the suite's logging as it was.
    configure_logging(Settings())
