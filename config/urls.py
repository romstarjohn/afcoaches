from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import healthz, spa_index

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("api/v1/", include("apps.api.urls")),
    path("admin/", admin.site.urls),
    # Everything else is a client-side route of the SPA (served by index.html).
    re_path(r"^(?!api/|admin/|static/)(?P<path>.*)$", spa_index, name="spa"),
]
