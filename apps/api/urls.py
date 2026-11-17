from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from apps.sync.views import SyncPushView

from .views import CsrfView, MeView

app_name = "api"

urlpatterns = [
    path("auth/csrf", CsrfView.as_view(), name="csrf"),
    path("auth/me", MeView.as_view(), name="me"),
    path("sync/push", SyncPushView.as_view(), name="sync-push"),
]

if settings.DEBUG:
    # OpenAPI schema for generating SPA types; not exposed in production.
    urlpatterns.append(path("schema", SpectacularAPIView.as_view(), name="schema"))
