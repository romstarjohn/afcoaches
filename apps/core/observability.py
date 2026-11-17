"""Logging configuration and request correlation. Rules: docs/observability.md.

Dev:  human-readable text, DEBUG for our own code, size-based rotation (5 MB x 5) in logs/dev/.
Prod: one JSON object per line (console + file), INFO, daily rotation (14 days) in logs/prod/.
Filters are attached to handlers (not loggers) so they also apply to records propagated from child loggers.
"""

import contextvars
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

# Set per request by apps.core.middleware.RequestLogMiddleware; "-" outside a request (commands, startup).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

DEV_MAX_BYTES = 5 * 1024 * 1024
DEV_BACKUPS = 5
PROD_BACKUP_DAYS = 14  # local retention; adjust together with the GDPR data inventory (DoD §2.6)

# Safety net only: callers must not log secrets or personal data in the first place.
_SENSITIVE = re.compile(
    r"(?i)\b(password|passwd|token|secret|authorization|cookie|sessionid|csrftoken|api[_-]?key)\b"
    r"(\s*[=:]\s*)((?:Bearer\s+|Basic\s+)?[^\s,;&]+)"
)
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "request_id"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SENSITIVE.sub(r"\1\2[redacted]", record.getMessage())
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, env: str) -> None:
        super().__init__()
        self.env = env

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "env": self.env,
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def _file_handler(path: Path, prod: bool, level: str | None = None) -> dict:
    handler: dict = {
        "filename": str(path),
        "encoding": "utf-8",
        "delay": True,  # the file is created on the first record, not at import time
        "formatter": "json" if prod else "text",
        "filters": ["request_id", "redact"],
    }
    if prod:
        handler |= {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": "midnight",
            "utc": True,
            "backupCount": PROD_BACKUP_DAYS,
        }
    else:
        handler |= {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": DEV_MAX_BYTES,
            "backupCount": DEV_BACKUPS,
        }
    if level:
        handler["level"] = level
    return handler


def build_logging(env: str, log_dir: Path | None, level: str | None = None) -> dict:
    """Return a ``LOGGING`` dict for ``env`` ("dev" or "prod"). ``log_dir=None`` means console only."""
    prod = env == "prod"
    level = (level or ("INFO" if prod else "DEBUG")).upper()
    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if prod else "text",
            "filters": ["request_id", "redact"],
        }
    }
    if log_dir is not None:
        handlers["file"] = _file_handler(log_dir / "app.log", prod)
        handlers["error_file"] = _file_handler(log_dir / "error.log", prod, level="ERROR")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": "apps.core.observability.RequestIdFilter"},
            "redact": {"()": "apps.core.observability.RedactFilter"},
        },
        "formatters": {
            "text": {"format": "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"},
            "json": {"()": "apps.core.observability.JsonFormatter", "env": env},
        },
        "handlers": handlers,
        # Third-party loggers stay at INFO even when our own code logs at DEBUG.
        "root": {"handlers": list(handlers), "level": "INFO" if level == "DEBUG" else level},
        "loggers": {
            "apps": {"level": level},
            # SQL statements carry parameters (personal/health data): never below INFO.
            "django.db.backends": {"level": "INFO"},
        },
    }
