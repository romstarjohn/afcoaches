import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import translation

pytestmark = pytest.mark.django_db


def test_custom_user_model_is_active():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model()._meta.app_label == "accounts"


def test_healthz_reports_database_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_default_language(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == "/fr/"


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("fr", "Bienvenue sur Coach sur mesure"),
        ("en", "Welcome to Coach sur mesure"),
    ],
)
def test_home_renders_in_each_language(client, lang, expected):
    with translation.override(lang):
        url = reverse("core:home")
    response = client.get(url)
    assert response.status_code == 200
    body = response.content.decode()
    assert expected in body
    assert f'<html lang="{lang}">' in body


def test_language_switch_redirects_to_translated_url(client):
    response = client.post(reverse("set_language"), {"language": "en", "next": "/fr/"})
    assert response.status_code == 302
    assert response["Location"] == "/en/"


def test_supported_languages_are_fr_and_en():
    assert [code for code, _ in settings.LANGUAGES] == ["fr", "en"]
    assert settings.LANGUAGE_CODE == "fr"
