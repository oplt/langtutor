from __future__ import annotations

SKIP_HTTP_ACCESS_LOG_PATHS: frozenset[str] = frozenset(
    {
        "/metrics",
        "/health",
        "/healthz",
        "/ready",
    }
)


def should_log_http_request(path: str) -> bool:
    """Return False for probe/scrape endpoints that should not spam access logs."""
    return path not in SKIP_HTTP_ACCESS_LOG_PATHS
