import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_create_user_uses_email_and_defaults():
    user = User.objects.create_user("Bob@Example.invalid", "a-long-test-password")
    assert user.email == "bob@example.invalid"
    assert user.role == "member"
    assert user.language == "en"
    assert user.email_verified is False
    assert user.check_password("a-long-test-password")
    assert not user.is_staff


def test_email_is_unique():
    User.objects.create_user("bob@example.invalid", "a-long-test-password")
    with pytest.raises(IntegrityError):
        User.objects.create_user("bob@example.invalid", "another-long-password")


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user("", "a-long-test-password")


def test_create_superuser():
    admin = User.objects.create_superuser("admin@example.invalid", "a-long-test-password")
    assert admin.is_staff and admin.is_superuser


def test_me_returns_profile(client):
    from rest_framework.test import APIClient

    user = User.objects.create_user("bob@example.invalid", "a-long-test-password", display_name="Bob", language="en")
    api = APIClient()
    api.force_login(user)
    data = api.get("/api/v1/auth/me").json()
    assert data["email"] == "bob@example.invalid"
    assert data["display_name"] == "Bob"
    assert data["language"] == "en"
    assert data["role"] == "member"
