"""Request correlation id and one access-log line per request (see docs/observability.md)."""

import logging
import re
import time
import uuid

from .observability import request_id_var

logger = logging.getLogger("apps.core.request")

# Accept a client/proxy supplied id only if it is harmless (no log injection, bounded size).
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_QUIET_PREFIXES = ("/healthz", "/assets/", "/static/", "/sw.js", "/manifest.webmanifest")


class RequestLogMiddleware:
    """Must be first in MIDDLEWARE so it wraps everything, including the response headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _VALID_ID.match(supplied) else uuid.uuid4().hex
        # Not reset here: Django logs 4xx/5xx ("django.request") after the middleware chain returns, and
        # those lines need the id too. It is cleared on the request_finished signal instead.
        request_id_var.set(request_id)
        started = time.perf_counter()
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        user = getattr(request, "user", None)
        level = logging.DEBUG if request.path.startswith(_QUIET_PREFIXES) else logging.INFO
        logger.log(
            level,
            "%s %s %s %sms",
            request.method,
            request.path,  # never the query string: it can carry personal data
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user.pk if user is not None and user.is_authenticated else None,
            },
        )
        return response


def clear_request_id(sender, **kwargs) -> None:
    request_id_var.set("-")
