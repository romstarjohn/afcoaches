import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()
RESET, CONFIRM, LOGIN, ME = (
    "/api/v1/auth/password-reset",
    "/api/v1/auth/password-reset/confirm",
    "/api/v1/auth/login",
    "/api/v1/auth/me",
)
OLD, NEW = "a-long-test-password", "a-brand-new-password"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user("ada@example.invalid", OLD, display_name="Ada")


@pytest.fixture
def api():
    return APIClient(enforce_csrf_checks=True)


def link_params(message=None):
    message = message or mail.outbox[-1]
    url = re.search(r"https?://\S+/reset-password\?\S+", message.body).group(0)
    query = parse_qs(urlparse(url).query)
    return {"uid": query["uid"][0], "token": query["token"][0]}


def request_reset(api, email="ada@example.invalid"):
    return api.post(RESET, {"email": email}, format="json")


def test_reset_request_sends_a_link_to_the_user(api, user):
    response = request_reset(api, "ADA@example.invalid")
    assert (response.status_code, response.json()) == (202, {"status": "reset_requested"})
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ada@example.invalid"]
    assert "Ada" in mail.outbox[0].body


def test_email_is_in_the_users_language(api):
    User.objects.create_user("ada@example.invalid", OLD, display_name="Ada", language="fr")
    request_reset(api)
    assert mail.outbox[0].subject == "Réinitialisez votre mot de passe"


def test_unknown_and_inactive_accounts_get_the_same_answer_and_no_mail(api, user):
    User.objects.create_user("off@example.invalid", OLD, is_active=False)
    known = request_reset(api)
    mail.outbox.clear()
    cache.clear()
    unknown = request_reset(api, "nobody@example.invalid")
    inactive = request_reset(api, "off@example.invalid")
    assert (unknown.status_code, unknown.json()) == (inactive.status_code, inactive.json())
    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert mail.outbox == []


def test_same_address_is_not_mailed_again_within_the_cooldown(api, user):
    for _ in range(3):
        request_reset(api)
    assert len(mail.outbox) == 1


def test_confirm_sets_the_new_password(api, user):
    request_reset(api)
    response = api.post(CONFIRM, {**link_params(), "password": NEW}, format="json")
    assert (response.status_code, response.json()) == (200, {"status": "password_changed"})
    user.refresh_from_db()
    assert user.check_password(NEW)
    assert not user.check_password(OLD)
    assert "_auth_user_id" not in api.session  # not logged in automatically


def test_link_works_only_once(api, user):
    request_reset(api)
    params = link_params()
    assert api.post(CONFIRM, {**params, "password": NEW}, format="json").status_code == 200
    again = api.post(CONFIRM, {**params, "password": "yet-another-password-1"}, format="json")
    assert (again.status_code, again.json()) == (400, {"code": "invalid_or_expired_token"})
    user.refresh_from_db()
    assert user.check_password(NEW)


def test_expired_link_is_rejected(api, user, settings):
    request_reset(api)
    settings.PASSWORD_RESET_TIMEOUT = -1
    response = api.post(CONFIRM, {**link_params(), "password": NEW}, format="json")
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password(OLD)


@pytest.mark.parametrize("tamper", ["uid", "token", "both"])
def test_tampered_or_foreign_link_is_rejected(api, user, tamper):
    other = User.objects.create_user("bob@example.invalid", OLD)
    request_reset(api)
    params = link_params()
    if tamper in ("uid", "both"):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        params["uid"] = urlsafe_base64_encode(force_bytes(other.pk))
    if tamper in ("token", "both"):
        params["token"] = params["token"][:-1] + ("a" if params["token"][-1] != "a" else "b")
    response = api.post(CONFIRM, {**params, "password": NEW}, format="json")
    assert response.status_code == 400
    other.refresh_from_db()
    assert other.check_password(OLD)


def test_garbage_input_is_rejected(api):
    response = api.post(CONFIRM, {"uid": "!!", "token": "x", "password": NEW}, format="json")
    assert (response.status_code, response.json()) == (400, {"code": "invalid_or_expired_token"})


def test_weak_password_is_rejected_and_link_stays_usable(api, user):
    request_reset(api)
    params = link_params()
    weak = api.post(CONFIRM, {**params, "password": "1234567890123"}, format="json")
    assert weak.status_code == 400
    assert "password" in weak.json()
    assert api.post(CONFIRM, {**params, "password": NEW}, format="json").status_code == 200


def test_reset_marks_email_as_verified(api, user):
    assert user.email_verified is False
    request_reset(api)
    api.post(CONFIRM, {**link_params(), "password": NEW}, format="json")
    user.refresh_from_db()
    assert user.email_verified is True


def test_existing_sessions_end_after_reset(api, user):
    other_device = APIClient()
    other_device.force_login(user)
    assert other_device.get(ME).status_code == 200
    request_reset(api)
    api.post(CONFIRM, {**link_params(), "password": NEW}, format="json")
    assert other_device.get(ME).status_code == 403


def test_reset_clears_the_login_lockout(api, user, settings):
    csrf = api.get("/api/v1/auth/csrf").json()["csrfToken"]
    api.credentials(HTTP_X_CSRFTOKEN=csrf)
    for _ in range(settings.LOGIN_MAX_FAILURES):
        api.post(LOGIN, {"email": user.email, "password": "wrong-password-123"}, format="json")
    assert api.post(LOGIN, {"email": user.email, "password": OLD}, format="json").status_code == 429
    request_reset(api)
    api.post(CONFIRM, {**link_params(), "password": NEW}, format="json")
    assert api.post(LOGIN, {"email": user.email, "password": NEW}, format="json").status_code == 200


def test_old_password_no_longer_logs_in(api, user):
    request_reset(api)
    api.post(CONFIRM, {**link_params(), "password": NEW}, format="json")
    api.credentials(HTTP_X_CSRFTOKEN=api.get("/api/v1/auth/csrf").json()["csrfToken"])
    assert api.post(LOGIN, {"email": user.email, "password": OLD}, format="json").status_code == 400


def test_link_uses_configured_site_url(api, user, settings):
    settings.SITE_URL = "https://app.example.invalid"
    request_reset(api)
    assert "https://app.example.invalid/reset-password?uid=" in mail.outbox[0].body


def test_french_email_body_is_translated(api):
    User.objects.create_user("ada@example.invalid", OLD, display_name="Ada", language="fr")
    request_reset(api)
    assert "Utilisez ce lien" in mail.outbox[0].body
