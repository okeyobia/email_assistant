from __future__ import annotations

import logging
import logging.config
from pathlib import Path

LOG_FILE_NAME = "email_assistant.log"


def configure_logging(log_dir: Path, level: str = "INFO") -> Path:
    """Configure console and file loggers."""

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE_NAME

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
            "console": {
                "format": "%(levelname)s | %(message)s",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": str(log_path),
                "maxBytes": 1_000_000,
                "backupCount": 3,
                "encoding": "utf-8",
            },
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
        },
        "root": {
            "handlers": ["file", "stdout"],
            "level": level.upper(),
        },
    }

    logging.config.dictConfig(config)
    logging.getLogger(__name__).debug("Logging configured at %s", level)
    return log_path
