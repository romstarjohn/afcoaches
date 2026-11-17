"""Security headers for the SPA and cache rules for PWA files."""

import re

# Strict CSP for the SPA: no inline scripts, no third-party origins. Django admin is excluded because
# it relies on inline styles; it is staff-only and protected by session + CSRF.
SPA_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "manifest-src 'self'",
        "worker-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/admin/"):
            response.setdefault("Content-Security-Policy", SPA_CSP)
        response.setdefault("Permissions-Policy", "camera=(self), geolocation=(), microphone=()")
        return response


# Vite emits content-hashed files under /assets/ -> safe to cache forever.
_HASHED = re.compile(r"^.+[.-][0-9a-zA-Z_-]{8,}\.\w+$")
_NO_CACHE = {"sw.js", "registerSW.js", "manifest.webmanifest", "index.html"}


def immutable_file_test(path: str, url: str) -> bool:
    return url.startswith("/assets/") and bool(_HASHED.match(url))


def add_pwa_headers(headers, path: str, url: str) -> None:
    """Service worker and manifest must never be cached long, or updates would not reach users."""
    if url.lstrip("/") in _NO_CACHE or url.startswith("/workbox-"):
        headers["Cache-Control"] = "no-cache"
    if url == "/sw.js":
        headers["Service-Worker-Allowed"] = "/"
