from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    """Liveness/readiness probe for hosting and monitoring; checks the database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001 - any DB failure means "not ready"
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


@require_GET
def spa_index(request, path=""):
    """Serve the SPA shell for every client-side route (deep links, reloads).

    Static build files (/assets/*, /sw.js, /manifest.webmanifest, icons) are served by WhiteNoise from
    SPA_DIST_DIR before this view is reached.
    """
    index = settings.SPA_DIST_DIR / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Frontend not built. Run `npm run build` in frontend/ or use the Vite dev server (port 5173).",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    response = HttpResponse(index.read_bytes(), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    return response
