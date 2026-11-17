from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from apps.sync.views import SyncPushView

from .views import (
    CsrfView,
    EmailChangeConfirmView,
    EmailChangeRequestView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeConfirmView,
    PasswordChangeRequestView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
    ResendVerificationView,
    VerifyEmailView,
)

app_name = "api"

urlpatterns = [
    path("auth/csrf", CsrfView.as_view(), name="csrf"),
    path("auth/register", RegisterView.as_view(), name="register"),
    path("auth/verify-email", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/resend-verification", ResendVerificationView.as_view(), name="resend-verification"),
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("auth/password-reset", PasswordResetView.as_view(), name="password-reset"),
    path("auth/password-reset/confirm", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/password-change/request", PasswordChangeRequestView.as_view(), name="password-change-request"),
    path("auth/password-change/confirm", PasswordChangeConfirmView.as_view(), name="password-change-confirm"),
    path("auth/email-change/request", EmailChangeRequestView.as_view(), name="email-change-request"),
    path("auth/email-change/confirm", EmailChangeConfirmView.as_view(), name="email-change-confirm"),
    path("auth/me", MeView.as_view(), name="me"),
    path("sync/push", SyncPushView.as_view(), name="sync-push"),
]

if settings.DEBUG:
    # OpenAPI schema for generating SPA types; not exposed in production.
    urlpatterns.append(path("schema", SpectacularAPIView.as_view(), name="schema"))
