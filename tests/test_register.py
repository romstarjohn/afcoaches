import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()
URL = "/api/v1/auth/register"
PAYLOAD = {
    "email": "New.User@Example.invalid",
    "password": "a-long-test-password",
    "display_name": "New User",
    "language": "fr",
}


@pytest.fixture(autouse=True)
def _clear_throttle():
    cache.clear()


@pytest.fixture
def api():
    return APIClient(enforce_csrf_checks=True)


def test_register_creates_unverified_member(api):
    response = api.post(URL, PAYLOAD, format="json")
    assert response.status_code == 202
    assert response.json() == {"status": "pending_verification"}
    user = User.objects.get(email="new.user@example.invalid")
    assert (user.role, user.email_verified, user.language, user.display_name) == ("member", False, "fr", "New User")
    assert user.check_password(PAYLOAD["password"])
    assert "_auth_user_id" not in api.session  # not logged in by registration


def test_language_defaults_to_english(api):
    api.post(URL, {k: v for k, v in PAYLOAD.items() if k != "language"}, format="json")
    assert User.objects.get().language == "en"


def test_existing_email_gets_identical_answer_and_is_not_changed(api):
    existing = User.objects.create_user("new.user@example.invalid", "original-password-1", display_name="Owner")
    response = api.post(URL, PAYLOAD, format="json")
    assert response.status_code == 202
    assert response.json() == {"status": "pending_verification"}
    assert User.objects.count() == 1
    existing.refresh_from_db()
    assert existing.display_name == "Owner"
    assert existing.check_password("original-password-1")


@pytest.mark.parametrize(
    "override,field",
    [
        ({"email": "not-an-email"}, "email"),
        ({"password": "short"}, "password"),
        ({"password": "1234567890123"}, "password"),
        ({"password": "password1234"}, "password"),
        ({"password": "new.user@example.invalid"}, "password"),
        ({"display_name": ""}, "display_name"),
        ({"language": "de"}, "language"),
    ],
)
def test_invalid_input_is_rejected(api, override, field):
    response = api.post(URL, {**PAYLOAD, **override}, format="json")
    assert response.status_code == 400
    assert field in response.json()
    assert User.objects.count() == 0


def test_password_is_never_echoed(api):
    response = api.post(URL, {**PAYLOAD, "password": "zq9"}, format="json")
    assert "zq9" not in response.content.decode()


def test_registration_is_rate_limited(api):
    for i in range(10):
        assert api.post(URL, {**PAYLOAD, "email": f"u{i}@example.invalid"}, format="json").status_code == 202
    assert api.post(URL, {**PAYLOAD, "email": "u11@example.invalid"}, format="json").status_code == 429
