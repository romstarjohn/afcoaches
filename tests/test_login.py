from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.permissions import IsEmailVerified

pytestmark = pytest.mark.django_db
User = get_user_model()
LOGIN, LOGOUT, ME = "/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/me"
PASSWORD = "a-long-test-password"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user("ada@example.invalid", PASSWORD, display_name="Ada", language="fr")


@pytest.fixture
def api():
    """Browser-like client: enforces CSRF and sends the token like the SPA does."""
    client = APIClient(enforce_csrf_checks=True)
    client.credentials(HTTP_X_CSRFTOKEN=client.get("/api/v1/auth/csrf").json()["csrfToken"])
    return client


def login(api, email="ada@example.invalid", password=PASSWORD):
    response = api.post(LOGIN, {"email": email, "password": password}, format="json")
    # Django rotates the CSRF token on login: like the SPA, fetch a fresh one afterwards.
    api.credentials(HTTP_X_CSRFTOKEN=api.get("/api/v1/auth/csrf").json()["csrfToken"])
    return response


def test_login_returns_profile_and_starts_session(api, user):
    response = login(api, "Ada@Example.invalid")
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "ada@example.invalid",
        "display_name": "Ada",
        "language": "fr",
        "role": "member",
        "email_verified": False,
    }
    assert api.get(ME).json()["email"] == "ada@example.invalid"


def test_unverified_user_can_log_in(api, user):
    assert user.email_verified is False
    assert login(api).status_code == 200


def test_session_key_is_rotated_on_login(api, user):
    api.get("/api/v1/auth/csrf")
    before = api.session.session_key
    login(api)
    assert api.session.session_key != before


@pytest.mark.parametrize(
    "email,password",
    [("ada@example.invalid", "wrong-password-123"), ("nobody@example.invalid", PASSWORD)],
)
def test_wrong_credentials_get_one_generic_error(api, user, email, password):
    response = login(api, email, password)
    assert response.status_code == 400
    assert response.json() == {"code": "invalid_credentials"}


def test_inactive_user_gets_the_generic_error(api):
    User.objects.create_user("off@example.invalid", PASSWORD, is_active=False)
    response = login(api, "off@example.invalid")
    assert (response.status_code, response.json()) == (400, {"code": "invalid_credentials"})


def test_login_requires_csrf_token():
    User.objects.create_user("ada@example.invalid", PASSWORD)
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(LOGIN, {"email": "ada@example.invalid", "password": PASSWORD}, format="json")
    assert response.status_code == 403


def test_lockout_after_max_failures_even_with_right_password(api, user, settings):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert login(api, password="wrong-password-123").status_code == 400
    locked = login(api)
    assert (locked.status_code, locked.json()) == (429, {"code": "too_many_attempts"})
    assert api.get(ME).status_code == 403


def test_lockout_applies_to_unknown_emails_identically(api, settings):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        login(api, "ghost@example.invalid", "wrong-password-123")
    assert login(api, "ghost@example.invalid").status_code == 429


def test_lockout_is_per_email(api, user, settings):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        login(api, "other@example.invalid", "wrong-password-123")
    assert login(api).status_code == 200


def test_successful_login_resets_the_failure_counter(api, user, settings):
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        login(api, password="wrong-password-123")
    assert login(api).status_code == 200
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        login(api, password="wrong-password-123")
    assert login(api).status_code == 200


def test_login_is_rate_limited_per_ip(api):
    rates = {"login": "3/hour", "anon": "1000/min"}
    with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, rates):
        for i in range(3):
            assert login(api, f"u{i}@example.invalid", "x" * 12).status_code == 400
        assert login(api, "u9@example.invalid", "x" * 12).status_code == 429


def test_logout_ends_the_session(api, user):
    login(api)
    assert api.post(LOGOUT).status_code == 204
    assert api.get(ME).status_code == 403


def test_logout_requires_login_and_csrf(api, user):
    assert api.post(LOGOUT).status_code == 403  # anonymous
    login(api)
    no_token = APIClient(enforce_csrf_checks=True)
    no_token.cookies = api.cookies
    assert no_token.post(LOGOUT).status_code == 403
    assert api.get(ME).status_code == 200  # session still alive


@pytest.mark.parametrize("verified,allowed", [(False, False), (True, True)])
def test_is_email_verified_permission(user, verified, allowed):
    user.email_verified = verified
    request = APIRequestFactory().get("/")
    request.user = user
    assert IsEmailVerified().has_permission(request, None) is allowed


def test_is_email_verified_denies_anonymous():
    from django.contrib.auth.models import AnonymousUser

    request = APIRequestFactory().get("/")
    request.user = AnonymousUser()
    assert IsEmailVerified().has_permission(request, None) is False
