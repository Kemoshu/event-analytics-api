import logging
import time

from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from prometheus_client.core import GaugeMetricFamily
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being served",
)

access_logger = logging.getLogger("app.access")

_EXCLUDED_PATHS = {"/metrics"}


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Records RED metrics and emits one structured access log line per request."""

    async def dispatch(self, request, call_next):
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        REQUESTS_IN_PROGRESS.inc()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            REQUESTS_IN_PROGRESS.dec()

            # Label with the route template, not the raw path, to bound cardinality.
            route = request.scope.get("route")
            path_label = route.path if route is not None else "unmatched"

            REQUEST_COUNT.labels(request.method, path_label, str(status_code)).inc()
            REQUEST_LATENCY.labels(request.method, path_label).observe(duration)

            access_logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "route": path_label,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client": request.client.host if request.client else None,
                },
            )


class DatabasePoolCollector:
    """Exposes SQLAlchemy connection pool state as gauges."""

    def __init__(self, engine):
        self._engine = engine

    def collect(self):
        pool = self._engine.pool
        stats = {
            "db_pool_size": ("Connections currently tracked by the pool", "size"),
            "db_pool_checked_out": ("Connections in use", "checkedout"),
            "db_pool_checked_in": ("Idle connections in the pool", "checkedin"),
            "db_pool_overflow": ("Connections beyond pool_size", "overflow"),
        }
        for metric_name, (doc, attr) in stats.items():
            getter = getattr(pool, attr, None)
            if getter is None:
                continue
            yield GaugeMetricFamily(metric_name, doc, value=float(getter()))


def register_db_pool_collector(engine) -> None:
    try:
        REGISTRY.register(DatabasePoolCollector(engine))
    except ValueError:
        # Already registered, e.g. app module imported twice under reload.
        pass
