import json
from datetime import timedelta
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import get_connection
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import VerificationCode
from apps.mailer.models import EmailOutbox
from apps.mailer.services import enqueue, process_due, purge_finished, register_renderer

pytestmark = pytest.mark.django_db
User = get_user_model()
Status = EmailOutbox.Status
REGISTER, RESET = "/api/v1/auth/register", "/api/v1/auth/password-reset"
PAYLOAD = {"email": "new@example.invalid", "password": "a-long-test-password", "display_name": "Nia", "language": "en"}


@pytest.fixture(autouse=True)
def _queue_only(settings):
    settings.MAILER_SEND_INLINE = False  # the point of this module: the request must not send


@pytest.fixture
def api():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user():
    return User.objects.create_user("ada@example.invalid", "a-long-test-password", display_name="Ada")


def test_smtp_connections_have_a_timeout(settings):
    assert settings.EMAIL_TIMEOUT > 0
    connection = get_connection("django.core.mail.backends.smtp.EmailBackend")
    assert connection.timeout == settings.EMAIL_TIMEOUT


def test_request_only_queues_and_the_worker_sends(api):
    assert api.post(REGISTER, PAYLOAD, format="json").status_code == 202
    assert mail.outbox == []
    entry = EmailOutbox.objects.get()
    assert (entry.kind, entry.status) == ("verification", Status.PENDING)

    assert process_due() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@example.invalid"]
    entry.refresh_from_db()
    assert entry.status == Status.SENT and entry.sent_at is not None


def test_nothing_is_sent_twice(api):
    api.post(REGISTER, PAYLOAD, format="json")
    process_due()
    assert process_due() == 0
    assert len(mail.outbox) == 1


def test_unknown_address_queues_nothing_known_address_queues_one(api, user):
    unknown = api.post(RESET, {"email": "nobody@example.invalid"}, format="json")
    assert EmailOutbox.objects.count() == 0
    known = api.post(RESET, {"email": user.email}, format="json")
    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert EmailOutbox.objects.count() == 1


def test_a_second_mail_of_the_same_kind_to_the_same_address_is_dropped(api, user):
    for _ in range(3):
        api.post(RESET, {"email": user.email}, format="json")
    assert EmailOutbox.objects.count() == 1


def test_the_cooldown_ends(api, user):
    api.post(RESET, {"email": user.email}, format="json")
    EmailOutbox.objects.update(created_at=timezone.now() - timedelta(seconds=120))
    api.post(RESET, {"email": user.email}, format="json")
    assert EmailOutbox.objects.count() == 2


def test_different_kinds_and_addresses_are_not_deduplicated(user):
    other = User.objects.create_user("bob@example.invalid", "a-long-test-password")
    enqueue("password_reset", user, to_key="a")
    enqueue("password_reset", other, to_key="b")
    enqueue("verification", user, to_key="a")
    assert EmailOutbox.objects.count() == 3


def test_no_token_link_or_code_is_stored_in_the_queue(api, user):
    api.post(RESET, {"email": user.email}, format="json")
    api.force_login(user)
    api.credentials(HTTP_X_CSRFTOKEN=api.get("/api/v1/auth/csrf").json()["csrfToken"])
    api.post("/api/v1/auth/password-change/request", {"current_password": "a-long-test-password"}, format="json")
    dump = json.dumps(list(EmailOutbox.objects.values()), default=str)
    assert "token" not in dump and "http" not in dump
    assert VerificationCode.objects.count() == 0  # the code only exists once the worker builds the mail

    process_due()
    assert VerificationCode.objects.count() == 1
    assert len(mail.outbox) == 2
    assert any("reset-password?uid=" in m.body for m in mail.outbox)


def test_failure_is_retried_with_backoff_and_then_succeeds(api):
    api.post(REGISTER, PAYLOAD, format="json")
    start = timezone.now()
    with mock.patch("apps.mailer.services.send_mail", side_effect=OSError("smtp down")):
        assert process_due(now=start) == 1
        entry = EmailOutbox.objects.get()
        assert (entry.status, entry.attempts) == (Status.PENDING, 1)
        assert "OSError" in entry.last_error
        assert entry.next_attempt_at > start
        assert process_due(now=start) == 0  # not due yet

    assert process_due(now=start + timedelta(seconds=61)) == 1
    entry.refresh_from_db()
    assert entry.status == Status.SENT and entry.last_error == ""
    assert len(mail.outbox) == 1


def test_backoff_doubles(api, settings):
    api.post(REGISTER, PAYLOAD, format="json")
    now = timezone.now()
    gaps = []
    with mock.patch("apps.mailer.services.send_mail", side_effect=OSError("down")):
        for _ in range(3):
            process_due(now=now)
            entry = EmailOutbox.objects.get()
            gaps.append(int((entry.next_attempt_at - now).total_seconds()))
            now = entry.next_attempt_at
    base = settings.MAILER_BACKOFF_SECONDS
    assert gaps == [base, base * 2, base * 4]


def test_gives_up_after_max_attempts(api, settings):
    api.post(REGISTER, PAYLOAD, format="json")
    now = timezone.now()
    with mock.patch("apps.mailer.services.send_mail", side_effect=OSError("down")) as failing:
        for _ in range(settings.MAILER_MAX_ATTEMPTS + 3):
            process_due(now=now)
            now += timedelta(days=1)
    entry = EmailOutbox.objects.get()
    assert (entry.status, entry.attempts) == (Status.FAILED, settings.MAILER_MAX_ATTEMPTS)
    assert failing.call_count == settings.MAILER_MAX_ATTEMPTS


def test_mail_no_longer_needed_is_skipped(api):
    api.post(REGISTER, PAYLOAD, format="json")
    User.objects.update(email_verified=True)  # verified before the worker got to it
    process_due()
    assert EmailOutbox.objects.get().status == Status.SKIPPED
    assert mail.outbox == []


def test_inactive_users_get_no_mail(api, user):
    api.post(RESET, {"email": user.email}, format="json")
    User.objects.update(is_active=False)
    process_due()
    assert EmailOutbox.objects.get().status == Status.SKIPPED
    assert mail.outbox == []


def test_unknown_kind_fails_without_looping(user):
    enqueue("does_not_exist", user)
    process_due()
    entry = EmailOutbox.objects.get()
    assert entry.status == Status.FAILED and "unknown" in entry.last_error
    assert process_due() == 0


def test_a_broken_renderer_is_retried_like_a_provider_error(user):
    @register_renderer("boom")
    def _boom(u, payload):
        raise RuntimeError("bug")

    enqueue("boom", user)
    process_due()
    entry = EmailOutbox.objects.get()
    assert (entry.status, entry.attempts) == (Status.PENDING, 1)


def test_one_bad_mail_does_not_block_the_others(user):
    other = User.objects.create_user("bob@example.invalid", "a-long-test-password", display_name="Bob")
    enqueue("does_not_exist", user)
    enqueue("password_reset", other)
    process_due()
    assert [m.to for m in mail.outbox] == [["bob@example.invalid"]]


def test_batch_limit(user):
    for i in range(3):
        enqueue("password_reset", user, to_key=f"k{i}")
    assert process_due(limit=2) == 2
    assert process_due(limit=2) == 1


def test_mails_are_sent_in_the_users_language(api):
    api.post(REGISTER, {**PAYLOAD, "language": "fr"}, format="json")
    process_due()
    assert mail.outbox[0].subject == "Confirmez votre adresse e-mail"


def test_queue_rows_disappear_with_the_user(user):
    enqueue("password_reset", user)
    user.delete()
    assert EmailOutbox.objects.count() == 0


def test_purge_removes_only_old_finished_rows(user, settings):
    old = timezone.now() - timedelta(days=settings.MAILER_RETENTION_DAYS + 1)
    for status in (Status.SENT, Status.FAILED, Status.SKIPPED, Status.PENDING):
        entry = EmailOutbox.objects.create(kind="password_reset", user=user, status=status)
        EmailOutbox.objects.filter(pk=entry.pk).update(created_at=old)
    EmailOutbox.objects.create(kind="password_reset", user=user, status=Status.SENT)  # recent
    assert purge_finished() == 3
    assert sorted(EmailOutbox.objects.values_list("status", flat=True)) == [Status.PENDING, Status.SENT]


def test_inline_mode_sends_immediately(user, settings):
    settings.MAILER_SEND_INLINE = True
    enqueue("password_reset", user)
    assert len(mail.outbox) == 1


def test_worker_command_once(api):
    api.post(REGISTER, PAYLOAD, format="json")
    out = StringIO()
    call_command("send_mail_outbox", "--once", stdout=out)
    assert len(mail.outbox) == 1
    assert "Handled 1" in out.getvalue()
    assert EmailOutbox.objects.get().status == Status.SENT


def _from_address(**env):
    """DEFAULT_FROM_EMAIL as a fresh process would compute it for the given environment."""
    import os
    import subprocess
    import sys

    code = (
        "import sys; sys.path.insert(0, '.'); import django; django.setup(); "
        "from django.conf import settings; print(settings.DEFAULT_FROM_EMAIL)"
    )
    base = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_CONTACT_")}
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        env={**base, "DJANGO_SETTINGS_MODULE": "config.settings", **env},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _readable(address_header):
    """(name, address) as a mail client shows them: non-ASCII names travel RFC 2047 encoded."""
    from email.header import decode_header, make_header
    from email.utils import parseaddr

    name, address = parseaddr(address_header)
    return str(make_header(decode_header(name))), address


def test_sender_comes_from_the_django_contact_variables():
    sender = _from_address(DJANGO_CONTACT_NAME="Équipe Coach", DJANGO_CONTACT_MAIL="hello@example.invalid")
    assert _readable(sender) == ("Équipe Coach", "hello@example.invalid")


def test_sender_falls_back_to_a_placeholder_without_configuration():
    assert _readable(_from_address()) == ("Coach sur mesure", "noreply@localhost")


def test_the_old_unprefixed_names_are_ignored():
    sender = _from_address(CONTACT_NAME="Wrong", CONTACT_MAIL="wrong@example.invalid")
    assert "wrong" not in sender.lower()


def test_queued_mails_use_the_configured_sender(api, settings):
    settings.DEFAULT_FROM_EMAIL = "Coach Test <contact@example.invalid>"
    api.post(REGISTER, PAYLOAD, format="json")
    process_due()
    assert mail.outbox[0].from_email == "Coach Test <contact@example.invalid>"
