"""Registry of entities that the offline-first SPA may write through /api/v1/sync/push.

Each feature that supports offline writes (e.g. client feedback in backlog 000015) registers one
handler. Handlers MUST:

- check permissions themselves (the push endpoint only guarantees an authenticated user),
- be idempotent: records are keyed by a client-generated UUID, so replaying an operation is safe,
- resolve concurrent edits with last-write-wins on ``client_updated_at`` unless the entity needs more.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

Status = Literal["applied", "conflict", "rejected"]


@dataclass(frozen=True)
class Operation:
    op_id: UUID
    entity: str
    record_id: UUID
    action: Literal["upsert", "delete"]
    data: dict[str, Any]
    client_updated_at: datetime


@dataclass(frozen=True)
class Result:
    status: Status
    error: str | None = None
    server_updated_at: datetime | None = None


class SyncRejected(Exception):
    """Raised by handlers for invalid data or missing permission; the client must not retry."""


class SyncConflict(Exception):
    """Raised by handlers when the server state forbids the change (e.g. entry locked after 24 h)."""


class SyncHandler(Protocol):
    entity: str

    def apply(self, user, op: Operation) -> Result: ...


_handlers: dict[str, SyncHandler] = {}


def register(handler: SyncHandler) -> SyncHandler:
    if handler.entity in _handlers:
        raise ValueError(f"sync handler already registered for entity {handler.entity!r}")
    _handlers[handler.entity] = handler
    return handler


def unregister(entity: str) -> None:
    _handlers.pop(entity, None)


def get_handler(entity: str) -> SyncHandler | None:
    return _handlers.get(entity)
