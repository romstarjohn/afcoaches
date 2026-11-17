import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import VerificationCode

pytestmark = pytest.mark.django_db
User = get_user_model()
PW_REQ, PW_CONFIRM = "/api/v1/auth/password-change/request", "/api/v1/auth/password-change/confirm"
EM_REQ, EM_CONFIRM = "/api/v1/auth/email-change/request", "/api/v1/auth/email-change/confirm"
ME, LOGIN = "/api/v1/auth/me", "/api/v1/auth/login"
OLD, NEW = "a-long-test-password", "a-brand-new-password"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user("ada@example.invalid", OLD, display_name="Ada")


def browser(user=None):
    """CSRF-enforcing client; logged in when a user is given."""
    client = APIClient(enforce_csrf_checks=True)
    if user:
        client.force_login(user)
    client.credentials(HTTP_X_CSRFTOKEN=client.get("/api/v1/auth/csrf").json()["csrfToken"])
    return client


@pytest.fixture
def api(user):
    return browser(user)


def code_from_outbox():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def token_from_outbox():
    url = re.search(r"https?://\S+\?\S+", mail.outbox[-1].body).group(0)
    return parse_qs(urlparse(url).query)["token"][0]


# ---- profile ---------------------------------------------------------------------------------


def test_profile_can_be_updated(api, user):
    response = api.patch(ME, {"display_name": "Ada L.", "language": "fr"}, format="json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert (user.display_name, user.language) == ("Ada L.", "fr")
    assert response.json()["language"] == "fr"


def test_profile_update_is_partial_and_validated(api, user):
    assert api.patch(ME, {"language": "fr"}, format="json").status_code == 200
    user.refresh_from_db()
    assert (user.display_name, user.language) == ("Ada", "fr")
    assert api.patch(ME, {"language": "de"}, format="json").status_code == 400
    assert api.patch(ME, {"display_name": ""}, format="json").status_code == 400


def test_profile_cannot_change_email_role_or_verification(api, user):
    api.patch(ME, {"email": "x@example.invalid", "role": "coach", "email_verified": True}, format="json")
    user.refresh_from_db()
    assert (user.email, user.role, user.email_verified) == ("ada@example.invalid", "member", False)


def test_profile_requires_login():
    assert browser().patch(ME, {"language": "fr"}, format="json").status_code == 403


# ---- password change (code by email) ----------------------------------------------------------


def request_code(api, password=OLD):
    return api.post(PW_REQ, {"current_password": password}, format="json")


def test_password_change_request_emails_a_six_digit_code(api, user):
    response = request_code(api)
    assert (response.status_code, response.json()) == (202, {"status": "code_sent"})
    assert mail.outbox[0].to == ["ada@example.invalid"]
    assert re.search(r"\b\d{6}\b", mail.outbox[0].body)
    assert VerificationCode.objects.get().code_hash != code_from_outbox()  # only a hash is stored


def test_password_change_request_needs_the_current_password(api):
    response = request_code(api, "wrong-password-123")
    assert (response.status_code, response.json()) == (400, {"code": "invalid_password"})
    assert mail.outbox == []


def test_wrong_current_password_counts_toward_the_lockout(api, settings):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        request_code(api, "wrong-password-123")
    assert request_code(api).status_code == 429
    assert mail.outbox == []


def test_password_change_with_code(api, user):
    request_code(api)
    response = api.post(PW_CONFIRM, {"code": code_from_outbox(), "new_password": NEW}, format="json")
    assert (response.status_code, response.json()) == (200, {"status": "password_changed"})
    user.refresh_from_db()
    assert user.check_password(NEW)
    assert api.get(ME).status_code == 200  # current session stays logged in


def test_other_sessions_end_after_password_change(api, user):
    other = APIClient()
    other.force_login(user)
    request_code(api)
    api.post(PW_CONFIRM, {"code": code_from_outbox(), "new_password": NEW}, format="json")
    assert other.get(ME).status_code == 403


def test_code_works_only_once(api, user):
    request_code(api)
    code = code_from_outbox()
    assert api.post(PW_CONFIRM, {"code": code, "new_password": NEW}, format="json").status_code == 200
    again = api.post(PW_CONFIRM, {"code": code, "new_password": "yet-another-password-1"}, format="json")
    assert (again.status_code, again.json()) == (400, {"code": "invalid_or_expired_code"})


def test_wrong_code_is_rejected_and_attempts_are_limited(api, user, settings):
    request_code(api)
    good = code_from_outbox()
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(settings.VERIFICATION_CODE_MAX_ATTEMPTS):
        assert api.post(PW_CONFIRM, {"code": wrong, "new_password": NEW}, format="json").status_code == 400
    # the code is void now, even the right one
    assert api.post(PW_CONFIRM, {"code": good, "new_password": NEW}, format="json").status_code == 400
    user.refresh_from_db()
    assert user.check_password(OLD)


def test_expired_code_is_rejected(api, user):
    request_code(api)
    VerificationCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    response = api.post(PW_CONFIRM, {"code": code_from_outbox(), "new_password": NEW}, format="json")
    assert response.status_code == 400


def test_code_without_request_is_rejected(api):
    assert api.post(PW_CONFIRM, {"code": "123456", "new_password": NEW}, format="json").status_code == 400


def test_weak_new_password_does_not_burn_an_attempt(api, user):
    request_code(api)
    code = code_from_outbox()
    assert api.post(PW_CONFIRM, {"code": code, "new_password": "1234567890123"}, format="json").status_code == 400
    assert VerificationCode.objects.get().attempts == 0
    assert api.post(PW_CONFIRM, {"code": code, "new_password": NEW}, format="json").status_code == 200


def test_code_of_another_user_does_not_work(api, user):
    other = User.objects.create_user("bob@example.invalid", OLD, display_name="Bob")
    other_api = browser(other)
    request_code(other_api)
    bobs_code = code_from_outbox()
    mail.outbox.clear()
    request_code(api)
    if bobs_code == code_from_outbox():
        pytest.skip("1-in-a-million: both users drew the same digits")
    assert api.post(PW_CONFIRM, {"code": bobs_code, "new_password": NEW}, format="json").status_code == 400
    other.refresh_from_db()
    assert other.check_password(OLD)


def test_password_change_endpoints_require_login():
    anonymous = browser()
    assert anonymous.post(PW_REQ, {"current_password": OLD}, format="json").status_code == 403
    assert anonymous.post(PW_CONFIRM, {"code": "123456", "new_password": NEW}, format="json").status_code == 403


def test_code_email_is_french_for_french_users():
    user = User.objects.create_user("fr@example.invalid", OLD, display_name="Fatou", language="fr")
    request_code(browser(user))
    assert mail.outbox[0].subject == "Votre code de vérification"
    assert "Votre code" in mail.outbox[0].body


# ---- email change (link to the new address) ---------------------------------------------------


def request_change(api, new="new@example.invalid", password=OLD):
    return api.post(EM_REQ, {"new_email": new, "current_password": password}, format="json")


def test_email_change_sends_link_to_the_new_address_and_does_not_change_yet(api, user):
    response = request_change(api, "New@Example.invalid")
    assert (response.status_code, response.json()) == (202, {"status": "confirmation_sent"})
    assert mail.outbox[0].to == ["new@example.invalid"]
    user.refresh_from_db()
    assert user.email == "ada@example.invalid"


def test_email_change_needs_the_current_password(api, user):
    response = request_change(api, password="wrong-password-123")
    assert (response.status_code, response.json()) == (400, {"code": "invalid_password"})
    assert mail.outbox == []


def test_email_change_link_applies_the_change(api, user):
    user.email_verified = False
    user.save()
    request_change(api)
    token = token_from_outbox()
    mail.outbox.clear()
    response = browser().post(EM_CONFIRM, {"token": token}, format="json")  # works logged out
    assert (response.status_code, response.json()) == (200, {"status": "email_changed"})
    user.refresh_from_db()
    assert (user.email, user.email_verified) == ("new@example.invalid", True)
    assert mail.outbox[0].to == ["ada@example.invalid"]  # old address is told
    assert "new@example.invalid" in mail.outbox[0].body


def test_email_change_link_works_once(api, user):
    request_change(api)
    token = token_from_outbox()
    assert browser().post(EM_CONFIRM, {"token": token}, format="json").status_code == 200
    assert browser().post(EM_CONFIRM, {"token": token}, format="json").status_code == 400


def test_login_uses_the_new_email_after_change(api, user):
    request_change(api)
    browser().post(EM_CONFIRM, {"token": token_from_outbox()}, format="json")
    fresh = browser()
    assert fresh.post(LOGIN, {"email": "new@example.invalid", "password": OLD}, format="json").status_code == 200
    assert browser().post(LOGIN, {"email": "ada@example.invalid", "password": OLD}, format="json").status_code == 400


def test_taken_email_gets_the_same_answer_and_the_owner_a_notice(api, user):
    User.objects.create_user("bob@example.invalid", OLD, display_name="Bob")
    free = request_change(api)
    free_body = (free.status_code, free.json())
    mail.outbox.clear()
    cache.clear()
    taken = request_change(api, "bob@example.invalid")
    assert (taken.status_code, taken.json()) == free_body
    assert mail.outbox[0].to == ["bob@example.invalid"]
    assert "verify" not in mail.outbox[0].body and "confirm-email-change" not in mail.outbox[0].body
    user.refresh_from_db()
    assert user.email == "ada@example.invalid"


def test_link_is_void_if_the_address_was_taken_meanwhile(api, user):
    request_change(api)
    token = token_from_outbox()
    User.objects.create_user("new@example.invalid", OLD)
    assert browser().post(EM_CONFIRM, {"token": token}, format="json").status_code == 400
    user.refresh_from_db()
    assert user.email == "ada@example.invalid"


def test_expired_or_forged_email_change_token_is_rejected(api, user, settings):
    request_change(api)
    token = token_from_outbox()
    assert browser().post(EM_CONFIRM, {"token": token + "x"}, format="json").status_code == 400
    settings.EMAIL_VERIFICATION_MAX_AGE = -1
    assert browser().post(EM_CONFIRM, {"token": token}, format="json").status_code == 400


def test_a_verification_token_cannot_be_used_as_email_change_token(user):
    from apps.accounts.emails import make_verification_token

    response = browser().post(EM_CONFIRM, {"token": make_verification_token(user)}, format="json")
    assert response.status_code == 400


def test_changing_to_the_current_email_does_nothing(api, user):
    assert request_change(api, "ada@example.invalid").status_code == 202
    assert mail.outbox == []


def test_email_change_request_requires_login():
    anonymous = browser()
    assert (
        anonymous.post(EM_REQ, {"new_email": "x@example.invalid", "current_password": OLD}, format="json").status_code
        == 403
    )
