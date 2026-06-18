"""Optional OpenTelemetry export (no-op when endpoint unset or SDK missing)."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.core.config import settings

logger = logging.getLogger(__name__)
_tracer: Any = None


def setup_tracing() -> None:
    global _tracer
    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.strip()
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("otel_sdk_unavailable install opentelemetry packages to export traces")
        return

    provider = TracerProvider(resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    )
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(settings.OTEL_SERVICE_NAME)
    logger.info("otel_tracing_enabled endpoint=%s", endpoint)


def get_tracer() -> Any:
    return _tracer


def start_span(name: str, **attributes: str):
    if _tracer is None:
        from contextlib import nullcontext

        return nullcontext()
    return _tracer.start_as_current_span(name, attributes=attributes)
