"""Prometheus instrumentation for the API.

A middleware records request count, in-flight gauge, and a latency histogram
(labelled by method + route template + status), from which Grafana derives
p50/p95/p99 via histogram_quantile. Low-cardinality by design: the route
*template* (not the raw path) is the label, so /kpis/{tenant_id} is one series.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUESTS = Counter(
    "foresight_api_requests_total",
    "API requests by method, route, and status.",
    ["method", "route", "status"],
)
IN_PROGRESS = Gauge(
    "foresight_api_requests_in_progress",
    "In-flight API requests.",
    ["method"],
)
LATENCY = Histogram(
    "foresight_api_request_duration_seconds",
    "API request latency by method and route.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
RATE_LIMITED = Counter(
    "foresight_api_rate_limited_total",
    "Requests rejected by the rate limiter.",
)
CACHE = Counter(
    "foresight_api_cache_total",
    "Response cache lookups by outcome.",
    ["outcome"],  # hit | miss
)


def _route(request: Request) -> str:
    """The matched route *template* (low cardinality). Populated only after
    routing, so read it after call_next; unmatched paths → 'unmatched'."""
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        method = request.method
        IN_PROGRESS.labels(method).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            IN_PROGRESS.labels(method).dec()
        route = _route(request)  # scope["route"] is set once routing has run
        LATENCY.labels(method, route).observe(time.perf_counter() - start)
        REQUESTS.labels(method, route, str(status)).inc()
        return response
