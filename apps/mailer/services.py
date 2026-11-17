"""Email outbox: queue mails during a request, deliver them from a separate worker.

Why: sending inside the request makes the answer slow (SMTP) and leaks, through the response time,
whether an account exists. Queued mails are also retried when the provider has a hiccup.

Delivery is at-least-once: a crash between "sent" and the database commit can cause one duplicate.
"""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailOutbox

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rendered:
    subject: str
    body: str
    to: str


# A renderer builds the final mail at send time. Returning None means "not needed any more".
Renderer = Callable[[object, dict], Rendered | None]
_renderers: dict[str, Renderer] = {}


def register_renderer(kind: str) -> Callable[[Renderer], Renderer]:
    def decorator(func: Renderer) -> Renderer:
        _renderers[kind] = func
        return func

    return decorator


def address_key(address: str) -> str:
    """Stable, non-reversible key for per-address de-duplication."""
    return hashlib.sha256(address.strip().lower().encode()).hexdigest()


def enqueue(kind: str, user, *, to_key: str = "", payload: dict | None = None) -> EmailOutbox | None:
    """Queues a mail. With `to_key`, a second mail of the same kind to the same address within
    MAILER_COOLDOWN_SECONDS is dropped (protects a mailbox from being flooded). The check lives in the
    database, so it holds across processes."""
    if to_key:
        since = timezone.now() - timedelta(seconds=settings.MAILER_COOLDOWN_SECONDS)
        if EmailOutbox.objects.filter(kind=kind, dedupe_key=to_key, created_at__gt=since).exists():
            return None
    entry = EmailOutbox.objects.create(kind=kind, user=user, payload=payload or {}, dedupe_key=to_key)
    if settings.MAILER_SEND_INLINE:  # development/tests only: no worker needed
        process_due()
    return entry


def _retry_or_fail(entry: EmailOutbox, error: Exception, now: datetime) -> None:
    entry.attempts += 1
    entry.last_error = f"{type(error).__name__}: {error}"[:200]
    if entry.attempts >= settings.MAILER_MAX_ATTEMPTS:
        entry.status = EmailOutbox.Status.FAILED
        logger.error("Mail %s #%s given up after %s attempts", entry.kind, entry.pk, entry.attempts)
    else:
        delay = settings.MAILER_BACKOFF_SECONDS * 2 ** (entry.attempts - 1)
        entry.next_attempt_at = now + timedelta(seconds=delay)
        logger.warning("Mail %s #%s failed (attempt %s), retrying in %ss", entry.kind, entry.pk, entry.attempts, delay)
    entry.save(update_fields=["status", "attempts", "last_error", "next_attempt_at"])


def _deliver(entry: EmailOutbox, now: datetime) -> None:
    renderer = _renderers.get(entry.kind)
    if renderer is None:
        entry.status, entry.last_error = EmailOutbox.Status.FAILED, "unknown mail kind"
        entry.save(update_fields=["status", "last_error"])
        return
    try:
        rendered = renderer(entry.user, entry.payload)
        if rendered is None:
            entry.status = EmailOutbox.Status.SKIPPED
            entry.save(update_fields=["status"])
            return
        send_mail(rendered.subject, rendered.body, None, [rendered.to])
    except Exception as error:  # noqa: BLE001 - provider outage, bad address, renderer bug: retry, then give up
        _retry_or_fail(entry, error, now)
        return
    entry.status, entry.sent_at, entry.last_error = EmailOutbox.Status.SENT, now, ""
    entry.save(update_fields=["status", "sent_at", "last_error"])
    logger.info("Mail %s #%s sent", entry.kind, entry.pk)


def process_due(limit: int = 50, now: datetime | None = None) -> int:
    """Delivers up to `limit` due mails and returns how many were handled.

    Each mail is claimed with a row lock (skip_locked), so several workers can run side by side
    without sending the same mail twice."""
    handled = 0
    for _ in range(limit):
        moment = now or timezone.now()
        with transaction.atomic():
            entry = (
                EmailOutbox.objects.select_for_update(skip_locked=True, of=("self",))
                .select_related("user")
                .filter(status=EmailOutbox.Status.PENDING, next_attempt_at__lte=moment)
                .order_by("id")
                .first()
            )
            if entry is None:
                break
            _deliver(entry, moment)
            handled += 1
    return handled


def purge_finished(now: datetime | None = None) -> int:
    """Deletes finished rows (sent, skipped, failed) after MAILER_RETENTION_DAYS: data minimisation."""
    cutoff = (now or timezone.now()) - timedelta(days=settings.MAILER_RETENTION_DAYS)
    deleted, _ = EmailOutbox.objects.exclude(status=EmailOutbox.Status.PENDING).filter(created_at__lt=cutoff).delete()
    return deleted
