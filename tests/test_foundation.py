import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.core.security import add_pwa_headers, immutable_file_test

pytestmark = pytest.mark.django_db


def test_custom_user_model_is_active():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model()._meta.app_label == "accounts"


def test_healthz_reports_database_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_supported_languages_are_fr_and_en():
    assert [code for code, _ in settings.LANGUAGES] == ["fr", "en"]
    assert settings.LANGUAGE_CODE == "en"


@pytest.fixture
def spa_dist(tmp_path, settings):
    (tmp_path / "index.html").write_text("<!doctype html><title>SPA shell</title>")
    settings.SPA_DIST_DIR = tmp_path
    return tmp_path


@pytest.mark.parametrize("path", ["/", "/plans/123", "/fr/coach/abc?x=1"])
def test_spa_shell_served_for_client_routes(client, spa_dist, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b"SPA shell" in response.content
    assert response["Cache-Control"] == "no-cache"


def test_spa_missing_build_returns_503(client, tmp_path, settings):
    settings.SPA_DIST_DIR = tmp_path / "missing"
    assert client.get("/").status_code == 503


def test_api_and_admin_are_not_swallowed_by_spa(client, spa_dist):
    assert client.get("/api/v1/does-not-exist").status_code == 404
    assert client.get("/admin/login/").status_code == 200


def test_csp_on_spa_but_not_on_admin(client, spa_dist):
    csp = client.get("/")["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "Content-Security-Policy" not in client.get("/admin/login/")


def test_pwa_cache_rules():
    headers = {}
    add_pwa_headers(headers, "", "/sw.js")
    assert headers == {"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"}
    headers = {}
    add_pwa_headers(headers, "", "/manifest.webmanifest")
    assert headers["Cache-Control"] == "no-cache"
    assert immutable_file_test("", "/assets/index-BmX3k9aQ.js")
    assert not immutable_file_test("", "/sw.js")


def test_whitenoise_serves_spa_files_with_pwa_headers(tmp_path, settings):
    """Boots WhiteNoise against a fake SPA build, like production does."""
    from whitenoise.middleware import WhiteNoiseMiddleware

    (tmp_path / "assets").mkdir()
    (tmp_path / "sw.js").write_text("self.addEventListener('fetch', () => {})")
    (tmp_path / "assets" / "index-AbCd1234.js").write_text("console.log(1)")
    (tmp_path / "manifest.webmanifest").write_text("{}")
    settings.WHITENOISE_ROOT = tmp_path
    middleware = WhiteNoiseMiddleware(lambda request: None)

    sw = middleware.files["/sw.js"].get_response("GET", {})
    sw.file.close()
    sw_headers = dict(sw.headers)
    assert sw_headers["Cache-Control"] == "no-cache"
    assert sw_headers["Service-Worker-Allowed"] == "/"
    manifest = middleware.files["/manifest.webmanifest"].get_response("GET", {})
    manifest.file.close()
    assert dict(manifest.headers)["Content-Type"] == "application/manifest+json"
    asset = middleware.files["/assets/index-AbCd1234.js"].get_response("GET", {})
    asset.file.close()
    assert "immutable" in dict(asset.headers)["Cache-Control"]
