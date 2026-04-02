"""Health check views for liveness and readiness probes.

/health/       — liveness: confirms the process is running
/health/ready/ — readiness: confirms DB and Redis are reachable
"""

import json

from django.conf import settings
from django.db import connection, OperationalError
from django.http import JsonResponse

try:
    import redis as redis_lib
except ImportError:
    redis_lib = None


def liveness(request):
    """Liveness probe — always returns 200 if the process is alive."""
    return JsonResponse({"status": "ok"})


def readiness(request):
    """Readiness probe — checks DB and Redis connectivity."""
    checks = {}
    ok = True

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except OperationalError as exc:
        checks["database"] = f"error: {exc}"
        ok = False

    # Redis check
    try:
        if redis_lib is None:
            raise RuntimeError("redis package is not installed")
        redis_url = settings.CELERY_BROKER_URL
        client = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        ok = False

    status_code = 200 if ok else 503
    return JsonResponse({"status": "ok" if ok else "degraded", "checks": checks}, status=status_code)
