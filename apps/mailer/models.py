from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailOutbox(models.Model):
    """One email waiting to be sent by the worker (`manage.py send_mail_outbox`).

    Deliberately stores no rendered content, tokens or codes: only who, which kind of mail and a small
    non-secret payload. Links and codes are created at send time, so a database dump never contains
    a usable reset link.
    """

    class Status(models.TextChoices):
        PENDING = "pending"
        SENT = "sent"
        FAILED = "failed"  # gave up after MAILER_MAX_ATTEMPTS
        SKIPPED = "skipped"  # no longer needed when its turn came (e.g. already verified)

    kind = models.CharField(max_length=40)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    payload = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="outbox_due_idx"),
            models.Index(fields=["kind", "dedupe_key", "created_at"], name="outbox_dedupe_idx"),
        ]

    def __str__(self):
        return f"{self.kind} #{self.pk} ({self.status})"
