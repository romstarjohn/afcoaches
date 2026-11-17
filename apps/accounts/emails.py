"""Tokens and transactional emails for accounts.

The API only *queues* mails (`queue_*`, see apps.mailer). The worker builds each mail at send time with
the matching `_render_*` function, so links and codes are never stored in the queue.
"""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils import translation
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _

from apps.mailer.services import Rendered, address_key, enqueue, register_renderer

from . import codes
from .models import User, VerificationCode

VERIFY_SALT = "accounts.verify-email"
EMAIL_CHANGE_SALT = "accounts.change-email"


# ---- tokens ------------------------------------------------------------------------------------


def make_verification_token(user: User) -> str:
    """Signed, expiring token. Bound to the current email, so changing the email invalidates it."""
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=VERIFY_SALT)


def user_for_verification_token(token: str) -> User | None:
    try:
        payload = signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)
        return User.objects.get(pk=payload["uid"], email=payload["email"], is_active=True)
    except (signing.BadSignature, KeyError, TypeError, User.DoesNotExist):
        return None


def user_for_reset_token(uid: str, token: str) -> User | None:
    """Django's token generator binds the token to the password hash and last login: it works once."""
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uid).decode(), is_active=True)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError, User.DoesNotExist):
        return None
    return user if default_token_generator.check_token(user, token) else None


def user_and_new_email_for_change_token(token: str) -> tuple[User, str] | None:
    """Token is bound to the old and the new address: it is void once the email has changed."""
    try:
        payload = signing.loads(token, salt=EMAIL_CHANGE_SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)
        user = User.objects.get(pk=payload["uid"], email=payload["old"], is_active=True)
        return user, payload["new"]
    except (signing.BadSignature, KeyError, TypeError, User.DoesNotExist):
        return None


# ---- queueing (called from the API; cheap, no mail is built or sent here) -----------------------


def queue_verification_email(user: User) -> None:
    enqueue("verification", user, to_key=address_key(user.email))


def queue_already_registered_email(user: User) -> None:
    enqueue("already_registered", user, to_key=address_key(user.email))


def queue_password_reset_email(user: User) -> None:
    enqueue("password_reset", user, to_key=address_key(user.email))


def queue_password_change_code(user: User) -> None:
    enqueue("password_change_code", user, to_key=address_key(user.email))


def queue_email_change_link(user: User, new_email: str) -> None:
    """For the NEW address; the change only happens when the link is opened."""
    enqueue("email_change_link", user, to_key=address_key(new_email), payload={"new_email": new_email})


def queue_email_changed_notice(user: User, old_email: str) -> None:
    """For the OLD address after the change, so a hijacked account does not go unnoticed."""
    enqueue("email_changed_notice", user, payload={"old_email": old_email})


# ---- rendering (called by the worker at send time) ----------------------------------------------


@register_renderer("verification")
def _render_verification(user: User, payload: dict) -> Rendered | None:
    if not user.is_active or user.email_verified:
        return None  # verified in the meantime
    link = f"{settings.SITE_URL}/verify-email?{urlencode({'token': make_verification_token(user)})}"
    with translation.override(user.language):
        return Rendered(
            _("Confirm your email address"),
            _(
                "Hello %(name)s,\n\nPlease confirm your email address to finish setting up your account:\n"
                "%(link)s\n\nThe link is valid for 3 days. If you did not create an account, ignore this email."
            )
            % {"name": user.display_name, "link": link},
            user.email,
        )


@register_renderer("already_registered")
def _render_already_registered(user: User, payload: dict) -> Rendered | None:
    if not user.is_active:
        return None
    with translation.override(user.language):
        return Rendered(
            _("You already have an account"),
            _(
                "Hello %(name)s,\n\nSomeone tried to create an account with this email address, but you already "
                "have one. You can simply log in. If you forgot your password, use “Forgot password” on the login "
                "page.\n\nIf this was not you, ignore this email."
            )
            % {"name": user.display_name},
            user.email,
        )


@register_renderer("password_reset")
def _render_password_reset(user: User, payload: dict) -> Rendered | None:
    if not user.is_active:
        return None
    query = urlencode(
        {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user)}
    )
    with translation.override(user.language):
        return Rendered(
            _("Reset your password"),
            _(
                "Hello %(name)s,\n\nUse this link to choose a new password:\n%(link)s\n\n"
                "The link is valid for 2 hours and can be used once. If you did not ask for this, ignore this "
                "email: your password stays unchanged."
            )
            % {"name": user.display_name, "link": f"{settings.SITE_URL}/reset-password?{query}"},
            user.email,
        )


@register_renderer("password_change_code")
def _render_password_change_code(user: User, payload: dict) -> Rendered | None:
    if not user.is_active:
        return None
    code = codes.issue_code(user, VerificationCode.Purpose.PASSWORD_CHANGE)  # issued only now, at send time
    with translation.override(user.language):
        return Rendered(
            _("Your verification code"),
            _(
                "Hello %(name)s,\n\nYour code to change your password is: %(code)s\n\n"
                "It is valid for 10 minutes. If you did not ask for this, someone may know your password: "
                "please change it."
            )
            % {"name": user.display_name, "code": code},
            user.email,
        )


@register_renderer("email_change_link")
def _render_email_change_link(user: User, payload: dict) -> Rendered | None:
    if not user.is_active:
        return None
    new_email = payload["new_email"]
    token = signing.dumps({"uid": user.pk, "old": user.email, "new": new_email}, salt=EMAIL_CHANGE_SALT)
    link = f"{settings.SITE_URL}/confirm-email-change?{urlencode({'token': token})}"
    with translation.override(user.language):
        return Rendered(
            _("Confirm your new email address"),
            _(
                "Hello %(name)s,\n\nConfirm this address as the new email of your account:\n%(link)s\n\n"
                "The link is valid for 3 days. If you did not ask for this, ignore this email."
            )
            % {"name": user.display_name, "link": link},
            new_email,
        )


@register_renderer("email_changed_notice")
def _render_email_changed_notice(user: User, payload: dict) -> Rendered | None:
    with translation.override(user.language):
        return Rendered(
            _("Your email address was changed"),
            _(
                "Hello %(name)s,\n\nThe email address of your account was changed to %(new)s. If this was not "
                "you, reset your password immediately and contact us."
            )
            % {"name": user.display_name, "new": user.email},
            payload["old_email"],
        )
