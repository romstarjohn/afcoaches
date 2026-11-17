from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model, created before the first migration so it can evolve safely.

    Email login, roles and language preference are added in backlog 000002/000003.
    """
