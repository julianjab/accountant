"""Application logging setup.

Kept in one place so the level and destination are configuration rather than
scattered ``basicConfig`` calls, and so the uvicorn loggers end up formatted the
same way as the application's own.
"""

import logging
import logging.config
from typing import Any

from server.infrastructure.config.settings import Settings

_TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_JSON_FORMAT = (
    '{"time": "%(asctime)s", "level": "%(levelname)s", '
    '"logger": "%(name)s", "message": "%(message)s"}'
)


def _handler(settings: Settings) -> dict[str, Any]:
    if settings.log_file:
        return {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.log_file,
            "maxBytes": settings.log_file_max_bytes,
            "backupCount": settings.log_file_backups,
            "formatter": "default",
        }
    return {"class": "logging.StreamHandler", "stream": "ext://sys.stderr", "formatter": "default"}


def configure_logging(settings: Settings) -> None:
    level = settings.log_level.upper()

    logging.config.dictConfig(
        {
            "version": 1,
            # uvicorn installs its own loggers before this runs; leaving them
            # enabled but unconfigured would double every line.
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": _JSON_FORMAT if settings.log_format == "json" else _TEXT_FORMAT
                }
            },
            "handlers": {"default": _handler(settings)},
            "root": {"handlers": ["default"], "level": level},
            "loggers": {
                # The application's own level is what ACCOUNTANT_LOG_LEVEL means;
                # access logs stay at INFO so DEBUG does not drown in them.
                "server": {"level": level, "handlers": ["default"], "propagate": False},
                "uvicorn.error": {"level": "INFO", "handlers": ["default"], "propagate": False},
                "uvicorn.access": {"level": "INFO", "handlers": ["default"], "propagate": False},
            },
        }
    )
