"""Issue and check short numeric email codes (see VerificationCode)."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from .models import User, VerificationCode


def _hash(user: User, purpose: str, code: str) -> str:
    message = f"{user.pk}:{purpose}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def issue_code(user: User, purpose: str) -> str:
    """Creates (or replaces) the user's code for this purpose and returns the plain 6-digit code."""
    code = f"{secrets.randbelow(10**6):06d}"
    VerificationCode.objects.update_or_create(
        user=user,
        purpose=purpose,
        defaults={
            "code_hash": _hash(user, purpose, code),
            "expires_at": timezone.now() + timedelta(seconds=settings.VERIFICATION_CODE_TTL),
            "attempts": 0,
        },
    )
    return code


def check_code(user: User, purpose: str, code: str) -> bool:
    """True once for a correct, unexpired code. Wrong guesses are counted; too many void the code."""
    with transaction.atomic():
        entry = VerificationCode.objects.select_for_update().filter(user=user, purpose=purpose).first()
        if entry is None:
            return False
        if entry.expires_at <= timezone.now():
            entry.delete()
            return False
        if constant_time_compare(entry.code_hash, _hash(user, purpose, code)):
            entry.delete()  # single use
            return True
        entry.attempts += 1
        if entry.attempts >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
            entry.delete()
        else:
            entry.save(update_fields=["attempts"])
        return False
