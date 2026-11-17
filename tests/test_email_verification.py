import re
from unittest import mock
from urllib.parse import unquote

import pytest
from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.emails import VERIFY_SALT, make_verification_token

pytestmark = pytest.mark.django_db
User = get_user_model()
REGISTER = "/api/v1/auth/register"
VERIFY = "/api/v1/auth/verify-email"
RESEND = "/api/v1/auth/resend-verification"
PAYLOAD = {"email": "new@example.invalid", "password": "a-long-test-password", "display_name": "Nia", "language": "en"}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient(enforce_csrf_checks=True)


def token_from_outbox(message=None):
    message = message or mail.outbox[-1]
    return unquote(re.search(r"/verify-email\?token=([^\s]+)", message.body).group(1))


def test_registration_sends_verification_link_and_link_verifies(api):
    api.post(REGISTER, PAYLOAD, format="json")
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["new@example.invalid"]
    assert "Nia" in message.body

    response = api.post(VERIFY, {"token": token_from_outbox()}, format="json")
    assert response.status_code == 200
    assert response.json() == {"status": "verified"}
    assert User.objects.get().email_verified is True


def test_email_is_sent_in_the_users_language(api):
    api.post(REGISTER, {**PAYLOAD, "language": "fr"}, format="json")
    assert mail.outbox[0].subject == "Confirmez votre adresse e-mail"


def test_verifying_twice_is_harmless(api):
    api.post(REGISTER, PAYLOAD, format="json")
    token = token_from_outbox()
    assert api.post(VERIFY, {"token": token}, format="json").status_code == 200
    assert api.post(VERIFY, {"token": token}, format="json").status_code == 200


@pytest.mark.parametrize("token", ["", "garbage", "a:b:c"])
def test_invalid_token_is_rejected(api, token):
    response = api.post(VERIFY, {"token": token}, format="json")
    assert response.status_code == 400
    assert response.json() == {"code": "invalid_or_expired_token"} or "token" in response.json()


def test_token_with_wrong_salt_is_rejected(api):
    user = User.objects.create_user("new@example.invalid", "a-long-test-password")
    forged = signing.dumps({"uid": user.pk, "email": user.email}, salt="something-else")
    assert api.post(VERIFY, {"token": forged}, format="json").status_code == 400
    assert User.objects.get().email_verified is False


def test_expired_token_is_rejected(api, settings):
    user = User.objects.create_user("new@example.invalid", "a-long-test-password")
    token = make_verification_token(user)
    settings.EMAIL_VERIFICATION_MAX_AGE = -1
    assert api.post(VERIFY, {"token": token}, format="json").status_code == 400
    assert User.objects.get().email_verified is False


def test_token_is_void_after_email_change(api):
    user = User.objects.create_user("new@example.invalid", "a-long-test-password")
    token = make_verification_token(user)
    user.email = "other@example.invalid"
    user.save()
    assert api.post(VERIFY, {"token": token}, format="json").status_code == 400
    assert User.objects.get().email_verified is False


def test_inactive_user_cannot_verify(api):
    user = User.objects.create_user("new@example.invalid", "a-long-test-password", is_active=False)
    assert api.post(VERIFY, {"token": make_verification_token(user)}, format="json").status_code == 400


def test_registering_an_existing_email_sends_a_notice_without_link(api):
    User.objects.create_user("new@example.invalid", "original-password-1", display_name="Owner")
    response = api.post(REGISTER, PAYLOAD, format="json")
    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert "verify-email" not in mail.outbox[0].body
    assert mail.outbox[0].subject == "You already have an account"


def test_resend_for_unverified_user_sends_a_new_link(api):
    User.objects.create_user("new@example.invalid", "a-long-test-password", display_name="Nia")
    response = api.post(RESEND, {"email": "New@Example.invalid"}, format="json")
    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert api.post(VERIFY, {"token": token_from_outbox()}, format="json").status_code == 200


def test_resend_gives_same_answer_for_unknown_and_verified_emails(api):
    User.objects.create_user("done@example.invalid", "a-long-test-password", email_verified=True)
    unknown = api.post(RESEND, {"email": "nobody@example.invalid"}, format="json")
    verified = api.post(RESEND, {"email": "done@example.invalid"}, format="json")
    assert (unknown.status_code, unknown.json()) == (verified.status_code, verified.json()) == (202, unknown.json())
    assert mail.outbox == []


def test_same_address_is_not_mailed_again_within_the_cooldown(api):
    User.objects.create_user("new@example.invalid", "a-long-test-password")
    for _ in range(3):
        api.post(RESEND, {"email": "new@example.invalid"}, format="json")
    assert len(mail.outbox) == 1


def test_mail_outage_does_not_change_the_answer(api):
    with mock.patch("apps.mailer.services.send_mail", side_effect=OSError("smtp down")):
        response = api.post(REGISTER, PAYLOAD, format="json")
    assert response.status_code == 202
    assert User.objects.count() == 1


def test_link_uses_configured_site_url_not_the_host_header(api, settings):
    settings.SITE_URL = "https://app.example.invalid"
    settings.ALLOWED_HOSTS = ["testserver", "evil.example"]
    api.post(REGISTER, PAYLOAD, format="json", HTTP_HOST="evil.example")
    assert "https://app.example.invalid/verify-email?token=" in mail.outbox[0].body
    assert "evil.example" not in mail.outbox[0].body


def test_unused_salt_constant_matches_tokens():
    user = User.objects.create_user("new@example.invalid", "a-long-test-password")
    assert signing.loads(make_verification_token(user), salt=VERIFY_SALT)["uid"] == user.pk
