import pytest


@pytest.fixture(autouse=True)
def _send_mail_inline(settings):
    """Most tests check the content of mails, so they deliver at once instead of running the worker.
    The queueing behaviour itself is covered in test_mailer.py, which switches this off."""
    settings.MAILER_SEND_INLINE = True
