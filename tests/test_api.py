import uuid
from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.sync import registry
from apps.sync.registry import Result, SyncConflict, SyncRejected

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user("alice", "alice@example.invalid", "a-long-test-password")


@pytest.fixture
def api(user):
    """Client that enforces CSRF like a real browser."""
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    token = client.get("/api/v1/auth/csrf").json()["csrfToken"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client


class MemoryHandler:
    """Test-only handler: last-write-wins upserts kept in memory."""

    entity = "test_note"

    def __init__(self):
        self.store = {}

    def apply(self, user, op):
        if op.data.get("text") == "forbidden":
            raise SyncRejected("not_allowed")
        if op.data.get("text") == "locked":
            raise SyncConflict("locked")
        current = self.store.get(op.record_id)
        if current is None or current["client_updated_at"] < op.client_updated_at:
            self.store[op.record_id] = {"data": op.data, "client_updated_at": op.client_updated_at}
        return Result("applied", server_updated_at=datetime(2026, 1, 1, tzinfo=UTC))


@pytest.fixture
def handler():
    h = registry.register(MemoryHandler())
    yield h
    registry.unregister(h.entity)


def op(text, entity="test_note", record_id=None, ts="2026-11-17T10:00:00Z"):
    return {
        "op_id": str(uuid.uuid4()),
        "entity": entity,
        "id": str(record_id or uuid.uuid4()),
        "action": "upsert",
        "data": {"text": text},
        "client_updated_at": ts,
    }


def test_csrf_endpoint_returns_token_and_sets_cookie():
    response = APIClient().get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrfToken"]
    assert "csrftoken" in response.cookies
    assert response.cookies["csrftoken"]["httponly"]


def test_me_requires_login():
    assert APIClient().get("/api/v1/auth/me").status_code == 403


def test_me_returns_current_user(api, user):
    body = api.get("/api/v1/auth/me").json()
    assert body == {"id": user.id, "username": "alice", "email": "alice@example.invalid"}


def test_api_rejects_non_json_renderer_requests(api):
    assert api.get("/api/v1/auth/me", HTTP_ACCEPT="text/html").status_code == 406


def test_sync_push_requires_csrf(user, handler):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.post("/api/v1/sync/push", {"operations": [op("hi")]}, format="json")
    assert response.status_code == 403


def test_sync_push_requires_login(handler):
    response = APIClient().post("/api/v1/sync/push", {"operations": [op("hi")]}, format="json")
    assert response.status_code == 403


def test_sync_push_mixed_batch_reports_each_operation(api, handler):
    ops = [op("hello"), op("forbidden"), op("locked"), op("x", entity="unknown")]
    response = api.post("/api/v1/sync/push", {"operations": ops}, format="json")
    assert response.status_code == 200
    statuses = [(r["op_id"], r["status"], r.get("error")) for r in response.json()["results"]]
    assert statuses == [
        (ops[0]["op_id"], "applied", None),
        (ops[1]["op_id"], "rejected", "not_allowed"),
        (ops[2]["op_id"], "conflict", "locked"),
        (ops[3]["op_id"], "rejected", "unknown_entity"),
    ]


def test_sync_push_is_idempotent_and_last_write_wins(api, handler):
    rid = uuid.uuid4()
    newer = op("new", record_id=rid, ts="2026-11-17T12:00:00Z")
    older = op("old", record_id=rid, ts="2026-11-17T08:00:00Z")
    for batch in ([newer], [newer], [older]):
        assert api.post("/api/v1/sync/push", {"operations": batch}, format="json").status_code == 200
    assert handler.store[rid]["data"] == {"text": "new"}


@pytest.mark.parametrize(
    "payload",
    [
        {"operations": []},
        {"operations": [op("x") for _ in range(101)]},
        {"operations": [{**op("x"), "action": "drop"}]},
        {"operations": [{**op("x"), "id": "not-a-uuid"}]},
    ],
)
def test_sync_push_validates_payload(api, handler, payload):
    assert api.post("/api/v1/sync/push", payload, format="json").status_code == 400


def test_schema_not_exposed_without_debug(api):
    assert api.get("/api/v1/schema").status_code == 404
