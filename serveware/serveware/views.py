import logging

from django.conf import settings
from django.db import connection
from django.http import Http404, JsonResponse

logger = logging.getLogger("serveware")


def healthz(request):
    """Liveness + DB readiness. Used by Docker HEALTHCHECK, smoke tests and Prometheus."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001 - any DB failure means unhealthy
        logger.exception("Health check failed: database unreachable")
        return JsonResponse({"status": "error", "db": "down"}, status=503)
    return JsonResponse(
        {"status": "ok", "db": "ok", "version": settings.APP_VERSION, "env": settings.DJANGO_ENV}
    )


def simulate_error(request):
    """Deliberate 500 for the monitoring incident simulation. Disabled unless the env flag is set."""
    if not settings.ENABLE_FAULT_INJECTION:
        raise Http404
    logger.warning("Fault injection endpoint triggered")
    raise RuntimeError("Simulated failure for monitoring demo")
