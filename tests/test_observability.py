import json
import logging
import logging.handlers
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.core.observability import JsonFormatter, RedactFilter, RequestIdFilter, build_logging, request_id_var

ROOT = Path(__file__).resolve().parent.parent

# The request tests hit /healthz, which queries the database; without this mark that query is blocked
# and /healthz would silently answer 503.
pytestmark = pytest.mark.django_db


def _record(msg="hello", *args, **extra):
    record = logging.LogRecord("apps.test", logging.INFO, __file__, 1, msg, args, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


# --- logging profiles -------------------------------------------------------------------------


def test_dev_profile_is_text_with_size_rotation(tmp_path):
    config = build_logging("dev", tmp_path / "dev")
    assert config["handlers"]["file"]["class"] == "logging.handlers.RotatingFileHandler"
    assert config["handlers"]["file"]["maxBytes"] > 0
    assert config["handlers"]["file"]["formatter"] == "text"
    assert config["loggers"]["apps"]["level"] == "DEBUG"
    assert config["loggers"]["django.db.backends"]["level"] == "INFO"  # SQL params may be personal data


def test_prod_profile_is_json_with_daily_rotation(tmp_path):
    config = build_logging("prod", tmp_path / "prod")
    assert config["handlers"]["file"]["class"] == "logging.handlers.TimedRotatingFileHandler"
    assert config["handlers"]["file"]["when"] == "midnight"
    assert config["handlers"]["file"]["backupCount"] == 14
    assert config["handlers"]["console"]["formatter"] == "json"
    assert config["loggers"]["apps"]["level"] == "INFO"
    assert config["handlers"]["error_file"]["level"] == "ERROR"


def test_log_level_override_and_console_only_fallback():
    config = build_logging("prod", None, "warning")
    assert list(config["handlers"]) == ["console"]
    assert config["root"]["level"] == "WARNING"


def test_config_is_valid_and_writes_rotating_file(tmp_path):
    import logging.config

    log_dir = tmp_path / "dev"
    log_dir.mkdir()
    config = build_logging("dev", log_dir)
    config["handlers"].pop("console")
    config["root"]["handlers"] = ["file", "error_file"]
    logging.config.dictConfig(config)
    try:
        logging.getLogger("apps.test").error("boom")
        for handler in logging.getLogger().handlers:
            handler.flush()
        assert "boom" in (log_dir / "app.log").read_text()
        assert "boom" in (log_dir / "error.log").read_text()
    finally:
        for handler in list(logging.getLogger().handlers):
            handler.close()
            logging.getLogger().removeHandler(handler)


# --- formatter and filters ---------------------------------------------------------------------


def test_json_formatter_emits_one_valid_object_with_context():
    token = request_id_var.set("abc12345")
    try:
        record = _record("synced %s ops", 3, coach_id=7)
        RequestIdFilter().filter(record)
        data = json.loads(JsonFormatter("prod").format(record))
    finally:
        request_id_var.reset(token)
    assert data["message"] == "synced 3 ops"
    assert data["request_id"] == "abc12345"
    assert data["level"] == "INFO"
    assert data["env"] == "prod"
    assert data["coach_id"] == 7
    assert data["ts"].endswith("+00:00")


@pytest.mark.parametrize(
    "message",
    [
        "login failed password=hunter2",
        "header Authorization: Bearer abc.def.ghi",
        "cookie: sessionid=xyz",
        "api_key=SECRET123 used",
    ],
)
def test_redact_filter_masks_secrets(message):
    record = _record(message)
    RedactFilter().filter(record)
    assert "[redacted]" in record.msg
    for secret in ("hunter2", "abc.def.ghi", "xyz", "SECRET123"):
        assert secret not in record.msg


def test_redact_filter_leaves_normal_messages_alone():
    record = _record("synced %s ops", 3)
    RedactFilter().filter(record)
    assert record.msg == "synced 3 ops"


# --- request middleware ---------------------------------------------------------------------------


def test_middleware_sets_request_id_and_logs_without_query_string(client, caplog):
    with caplog.at_level(logging.INFO, logger="apps.core.request"):
        response = client.get("/api/v1/does-not-exist?email=a@b.c")
    request_id = response["X-Request-ID"]
    assert len(request_id) == 32
    records = [r for r in caplog.records if r.name == "apps.core.request"]
    assert len(records) == 1
    assert records[0].status == 404
    assert records[0].path == "/api/v1/does-not-exist"
    assert records[0].duration_ms >= 0
    assert "a@b.c" not in caplog.text


def test_middleware_accepts_valid_and_rejects_unsafe_request_ids(client):
    assert client.get("/healthz", headers={"X-Request-ID": "trace-0001-abcd"})["X-Request-ID"] == "trace-0001-abcd"
    unsafe = client.get("/healthz", headers={"X-Request-ID": "bad id\r\ninjected"})["X-Request-ID"]
    assert unsafe != "bad id\r\ninjected" and len(unsafe) == 32


def test_healthz_is_logged_at_debug_only(client, caplog):
    with caplog.at_level(logging.INFO, logger="apps.core.request"):
        client.get("/healthz")
    assert not [r for r in caplog.records if r.name == "apps.core.request"]


# --- settings: env flag and log directory ---------------------------------------------------------
# Explicit variables always win over a local .env, so these tests do not depend on its contents.


def _import_settings(**env):
    base = {"PATH": os.environ.get("PATH", ""), "DATABASE_URL": "sqlite:///unused.db", "PYTHONWARNINGS": "ignore"}
    return subprocess.run(  # noqa: S603 - fixed argv, test-only
        [sys.executable, "-c", "import config.settings as s; print(s.APP_ENV, s.DEBUG, s.LOG_DIR)"],
        env={**base, "DJANGO_SETTINGS_MODULE": "config.settings", **env},
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dev_flag_creates_dev_log_directory(tmp_path):
    result = _import_settings(DJANGO_ENV="dev", DJANGO_DEBUG="true", DJANGO_LOG_DIR=str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[:2] == ["dev", "True"]
    assert (tmp_path / "dev").is_dir() and not (tmp_path / "prod").exists()


def test_prod_flag_creates_prod_log_directory(tmp_path):
    result = _import_settings(
        DJANGO_ENV="prod", DJANGO_DEBUG="false", DJANGO_SECRET_KEY="x" * 50, DJANGO_LOG_DIR=str(tmp_path)
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[:2] == ["prod", "False"]
    assert (tmp_path / "prod").is_dir() and not (tmp_path / "dev").exists()


@pytest.mark.parametrize(
    "env",
    [{"DJANGO_ENV": "staging"}, {"DJANGO_ENV": "prod", "DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": "x" * 50}],
)
def test_invalid_env_flag_combinations_are_rejected(env, tmp_path):
    result = _import_settings(DJANGO_LOG_DIR=str(tmp_path), **env)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_django_request_warnings_carry_the_request_id(client):
    """django.request logs 4xx after our middleware returns; the id must still be set then."""
    seen = []

    class Capture(logging.Handler):
        def emit(self, record):
            seen.append((record.name, request_id_var.get()))

    handler = Capture()
    logging.getLogger("django.request").addHandler(handler)
    try:
        response = client.get("/api/v1/does-not-exist")
    finally:
        logging.getLogger("django.request").removeHandler(handler)
    assert seen and all(rid == response["X-Request-ID"] for _, rid in seen)
    assert request_id_var.get() == "-"  # cleared on request_finished
