from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    """Custom user model: email is the login, no username.

    Roles beyond "member" (coach/client) are added in backlog 000003.
    """

    class Role(models.TextChoices):
        MEMBER = "member", _("Member")

    username = None
    email = models.EmailField(_("email address"), unique=True)
    display_name = models.CharField(_("display name"), max_length=80, blank=True)
    language = models.CharField(_("language"), max_length=2, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self):
        return self.email


class VerificationCode(models.Model):
    """Short-lived numeric code sent by email to confirm a sensitive action (one active per user+purpose).

    Only an HMAC of the code is stored. Persisted in the database (not the cache) so the attempt
    limit holds across workers and restarts.
    """

    class Purpose(models.TextChoices):
        PASSWORD_CHANGE = "password_change"  # noqa: S105 - a label, not a secret

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "purpose"], name="one_code_per_user_purpose")]

    def __str__(self):
        return f"{self.purpose} code for user {self.user_id}"
