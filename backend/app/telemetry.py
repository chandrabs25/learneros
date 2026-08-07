"""Optional OpenTelemetry setup for Phoenix or any OTLP-compatible collector."""

from __future__ import annotations

import logging
import os
from urllib.parse import unquote

from fastapi import FastAPI
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.config import settings


logger = logging.getLogger(__name__)
_provider: TracerProvider | None = None


def _headers(raw: str) -> dict[str, str] | None:
    if not raw.strip():
        return None
    headers: dict[str, str] = {}
    for item in raw.split(","):
        key, separator, value = item.partition("=")
        if separator and key.strip():
            headers[key.strip()] = unquote(value.strip())
    return headers or None


def configure_telemetry(app: FastAPI | None = None) -> None:
    """Configure tracing once. With OTEL_ENABLED=false this is a no-op."""
    global _provider
    if not settings.OTEL_ENABLED or _provider is not None:
        return

    if not settings.OTEL_CAPTURE_CONTENT:
        os.environ.setdefault("OPENINFERENCE_HIDE_INPUTS", "true")
        os.environ.setdefault("OPENINFERENCE_HIDE_OUTPUTS", "true")
        os.environ.setdefault("OPENINFERENCE_HIDE_INPUT_IMAGES", "true")

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.OTEL_SAMPLE_RATIO)),
    )
    exporter_kwargs = {}
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        exporter_kwargs["endpoint"] = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    parsed_headers = _headers(settings.OTEL_EXPORTER_OTLP_HEADERS)
    if parsed_headers:
        exporter_kwargs["headers"] = parsed_headers
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**exporter_kwargs)))
    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=provider,
            excluded_urls="health",
        )
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    _provider = provider
    logger.info("OpenTelemetry tracing enabled for %s", settings.OTEL_SERVICE_NAME)


def shutdown_telemetry() -> None:
    global _provider
    if _provider is None:
        return
    _provider.force_flush(timeout_millis=5000)
    _provider.shutdown()
    _provider = None
