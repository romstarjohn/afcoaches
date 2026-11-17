import hashlib

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import codes
from apps.accounts.emails import (
    queue_already_registered_email,
    queue_email_change_link,
    queue_email_changed_notice,
    queue_password_change_code,
    queue_password_reset_email,
    queue_verification_email,
    user_and_new_email_for_change_token,
    user_for_reset_token,
    user_for_verification_token,
)
from apps.accounts.models import VerificationCode


class StatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class CodeSerializer(serializers.Serializer):
    """Machine-readable reason of a refused request, e.g. invalid_credentials."""

    code = serializers.CharField()


class CsrfTokenSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()  # noqa: N815 - wire format


@method_decorator(ensure_csrf_cookie, name="dispatch")
@extend_schema(responses=CsrfTokenSerializer)
class CsrfView(APIView):
    """Hands the SPA a CSRF token for unsafe requests.

    Same-origin only (no CORS configured), so other sites cannot read the token. The cookie itself
    stays HttpOnly; the SPA sends the token back in the X-CSRFToken header.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    language = serializers.CharField()
    role = serializers.CharField()
    email_verified = serializers.BooleanField()


class ProfileSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=80, required=False)
    language = serializers.ChoiceField(choices=[code for code, _ in settings.LANGUAGES], required=False)


class MeView(APIView):
    """Current user (also for unverified accounts). 403 when not logged in (session auth)."""

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    @extend_schema(request=ProfileSerializer, responses=MeSerializer)
    def patch(self, request):
        """Profile: display name and preferred language."""
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save(update_fields=list(serializer.validated_data) or None)
        return Response(MeSerializer(user).data)


def _checked_password(password: str, user) -> str:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)}) from exc
    return password


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    display_name = serializers.CharField(max_length=80)
    language = serializers.ChoiceField(choices=[code for code, _ in settings.LANGUAGES], default=settings.LANGUAGE_CODE)

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        candidate = get_user_model()(email=attrs["email"], display_name=attrs["display_name"])
        attrs["password"] = _checked_password(attrs["password"], candidate)
        return attrs


@extend_schema(request=RegisterSerializer, responses={202: StatusSerializer})
class RegisterView(APIView):
    """Creates a member account (role "member", email not yet verified).

    The answer is identical whether or not the email is already registered (no account enumeration).
    New accounts get a verification email, existing ones an "already registered" notice.
    """

    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        User = get_user_model()
        existing = User.objects.filter(email=data["email"]).first()
        if existing is not None:
            queue_already_registered_email(existing)
        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        data["email"],
                        data["password"],
                        display_name=data["display_name"],
                        language=data["language"],
                    )
            except IntegrityError:
                pass  # concurrent registration of the same email: treat like "already registered"
            else:
                queue_verification_email(user)
        return Response({"status": "pending_verification"}, status=status.HTTP_202_ACCEPTED)


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=500)


@extend_schema(request=VerifyEmailSerializer, responses={200: StatusSerializer, 400: CodeSerializer})
class VerifyEmailView(APIView):
    """Confirms an email address from the link in the verification email. Idempotent."""

    permission_classes = [AllowAny]
    throttle_scope = "verify"

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = user_for_verification_token(serializer.validated_data["token"])
        if user is None:
            return Response({"code": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        return Response({"status": "verified"})


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


@extend_schema(request=ResendVerificationSerializer, responses={202: StatusSerializer})
class ResendVerificationView(APIView):
    """Sends a new verification email if the account exists and is unverified. Always answers 202."""

    permission_classes = [AllowAny]
    throttle_scope = "resend"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(email=serializer.validated_data["email"].strip().lower()).first()
        if user is not None and user.is_active and not user.email_verified:
            queue_verification_email(user)
        return Response({"status": "pending_verification"}, status=status.HTTP_202_ACCEPTED)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, max_length=128)


def _failure_key(email: str) -> str:
    return "login-failures:" + hashlib.sha256(email.encode()).hexdigest()


@method_decorator(csrf_protect, name="dispatch")
@extend_schema(request=LoginSerializer, responses={200: MeSerializer, 400: CodeSerializer, 429: CodeSerializer})
class LoginView(APIView):
    """Session login. Unverified accounts may log in (see apps.accounts.permissions.IsEmailVerified).

    One generic error for unknown email, wrong password and inactive account. After
    LOGIN_MAX_FAILURES failures per email the login is locked for LOGIN_LOCKOUT_SECONDS, even with the
    right password. The counter exists for unknown emails too, so lockout reveals nothing.
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        key = _failure_key(email)
        failures = cache.get(key, 0)
        if failures >= settings.LOGIN_MAX_FAILURES:
            return Response({"code": "too_many_attempts"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        user = authenticate(request, username=email, password=serializer.validated_data["password"])
        if user is None:
            cache.set(key, failures + 1, settings.LOGIN_LOCKOUT_SECONDS)
            return Response({"code": "invalid_credentials"}, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(key)
        login(request, user)  # rotates the session key
        return Response(MeSerializer(user).data)


@extend_schema(request=None, responses={204: None})
class LogoutView(APIView):
    """Ends the session. Needs a valid session and CSRF token (DRF enforces CSRF for session users)."""

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


@extend_schema(request=PasswordResetSerializer, responses={202: StatusSerializer})
class PasswordResetView(APIView):
    """Sends a reset link if an active account exists. Always answers 202 (no account enumeration)."""

    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(email=serializer.validated_data["email"].strip().lower()).first()
        if user is not None and user.is_active:
            queue_password_reset_email(user)
        return Response({"status": "reset_requested"}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


@extend_schema(request=PasswordResetConfirmSerializer, responses={200: StatusSerializer, 400: CodeSerializer})
class PasswordResetConfirmView(APIView):
    """Sets a new password from a reset link.

    The link proves control of the mailbox, so the email counts as verified. Changing the password
    invalidates every existing session of the user (Django checks the password hash stored in the
    session) and clears the login lockout. The user is not logged in automatically.
    """

    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = user_for_reset_token(data["uid"], data["token"])
        if user is None:
            return Response({"code": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(_checked_password(data["password"], user))
        user.email_verified = True
        user.save(update_fields=["password", "email_verified"])
        cache.delete(_failure_key(user.email))
        return Response({"status": "password_changed"})


def _password_is_wrong(user, password: str) -> Response | None:
    """Re-authentication for sensitive actions. Shares the login lockout counter, so a stolen session
    cannot be used to guess the password."""
    key = _failure_key(user.email)
    failures = cache.get(key, 0)
    if failures >= settings.LOGIN_MAX_FAILURES:
        return Response({"code": "too_many_attempts"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    if not user.check_password(password):
        cache.set(key, failures + 1, settings.LOGIN_LOCKOUT_SECONDS)
        return Response({"code": "invalid_password"}, status=status.HTTP_400_BAD_REQUEST)
    cache.delete(key)
    return None


class CurrentPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False, max_length=128)


@extend_schema(
    request=CurrentPasswordSerializer, responses={202: StatusSerializer, 400: CodeSerializer, 429: CodeSerializer}
)
class PasswordChangeRequestView(APIView):
    """Step 1 of changing the password in the app: re-enter the current password, get a code by email."""

    throttle_scope = "account"

    def post(self, request):
        serializer = CurrentPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        error = _password_is_wrong(request.user, serializer.validated_data["current_password"])
        if error is not None:
            return error
        queue_password_change_code(request.user)
        return Response({"status": "code_sent"}, status=status.HTTP_202_ACCEPTED)


class PasswordChangeConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


@extend_schema(request=PasswordChangeConfirmSerializer, responses={200: StatusSerializer, 400: CodeSerializer})
class PasswordChangeConfirmView(APIView):
    """Step 2: the emailed code plus the new password. Other sessions end, this one stays logged in."""

    throttle_scope = "account"

    def post(self, request):
        serializer = PasswordChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        # Validate the password first: a weak password must not burn one of the code's attempts.
        try:
            validate_password(serializer.validated_data["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        if not codes.check_code(user, VerificationCode.Purpose.PASSWORD_CHANGE, serializer.validated_data["code"]):
            return Response({"code": "invalid_or_expired_code"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        update_session_auth_hash(request, user)
        return Response({"status": "password_changed"})


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField(max_length=254)
    current_password = serializers.CharField(trim_whitespace=False, max_length=128)


@extend_schema(
    request=EmailChangeRequestSerializer, responses={202: StatusSerializer, 400: CodeSerializer, 429: CodeSerializer}
)
class EmailChangeRequestView(APIView):
    """Asks to change the login email. The address only changes once the link sent to the NEW address
    is opened. Same answer whether or not the new address already belongs to an account."""

    throttle_scope = "account"

    def post(self, request):
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        error = _password_is_wrong(user, serializer.validated_data["current_password"])
        if error is not None:
            return error
        new_email = serializer.validated_data["new_email"].strip().lower()
        if new_email != user.email:
            owner = get_user_model().objects.filter(email=new_email).first()
            if owner is not None:
                queue_already_registered_email(owner)
            else:
                queue_email_change_link(user, new_email)
        return Response({"status": "confirmation_sent"}, status=status.HTTP_202_ACCEPTED)


@extend_schema(request=VerifyEmailSerializer, responses={200: StatusSerializer, 400: CodeSerializer})
class EmailChangeConfirmView(APIView):
    """Applies the change from the emailed link (works logged out: the token is the proof)."""

    permission_classes = [AllowAny]
    throttle_scope = "verify"

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        found = user_and_new_email_for_change_token(serializer.validated_data["token"])
        invalid = Response({"code": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        if found is None:
            return invalid
        user, new_email = found
        old_email = user.email
        user.email = new_email
        user.email_verified = True  # the new address just proved itself
        try:
            with transaction.atomic():
                user.save(update_fields=["email", "email_verified"])
        except IntegrityError:
            return invalid  # the address was taken in the meantime
        queue_email_changed_notice(user, old_email)
        return Response({"status": "email_changed"})
