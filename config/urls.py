from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from apps.core.views import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("i18n/", include("django.conf.urls.i18n")),  # set_language view for the language switch
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    prefix_default_language=True,
)
