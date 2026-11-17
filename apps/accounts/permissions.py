from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    """Policy: unverified members may log in and read their own account, but not use features that
    act on other people or content (e.g. following a coach). Add this class to such endpoints."""

    code = "email_not_verified"
    message = "Please verify your email address first."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.email_verified)
