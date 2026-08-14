"""Optional OpenTelemetry setup for Phoenix or any OTLP-compatible collector."""

from __future__ import annotations

import logging
import os
from urllib.parse import unquote

from fastapi import FastAPI
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.config import settings


logger = logging.getLogger(__name__)
_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_logger_provider: LoggerProvider | None = None
_otel_log_handler: LoggingHandler | None = None


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
    """Configure telemetry once. With OTEL_ENABLED=false this is a no-op."""
    global _logger_provider, _meter_provider, _otel_log_handler, _provider
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

    metric_exporter_kwargs = dict(exporter_kwargs)
    metrics_endpoint = settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT
    if not metrics_endpoint and settings.OTEL_EXPORTER_OTLP_ENDPOINT.endswith("/v1/traces"):
        metrics_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.removesuffix("/v1/traces") + "/v1/metrics"
    if metrics_endpoint:
        metric_exporter_kwargs["endpoint"] = metrics_endpoint
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(**metric_exporter_kwargs),
        export_interval_millis=settings.OTEL_METRIC_EXPORT_INTERVAL_MS,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    logs_endpoint = settings.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT
    if not logs_endpoint and settings.OTEL_EXPORTER_OTLP_ENDPOINT.endswith("/v1/traces"):
        logs_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.removesuffix("/v1/traces") + "/v1/logs"
    if logs_endpoint:
        log_exporter_kwargs = {}
        if parsed_headers:
            log_exporter_kwargs["headers"] = parsed_headers
        log_exporter_kwargs["endpoint"] = logs_endpoint
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(**log_exporter_kwargs))
        )
        log_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger("app").addHandler(log_handler)
        _logger_provider = logger_provider
        _otel_log_handler = log_handler

    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=provider,
            excluded_urls="health",
        )
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    _provider = provider
    _meter_provider = meter_provider
    logger.info("OpenTelemetry tracing, metrics, and logs enabled for %s", settings.OTEL_SERVICE_NAME)


def shutdown_telemetry() -> None:
    global _logger_provider, _meter_provider, _otel_log_handler, _provider
    if _otel_log_handler is not None:
        logging.getLogger("app").removeHandler(_otel_log_handler)
        _otel_log_handler = None
    if _logger_provider is not None:
        _logger_provider.force_flush(timeout_millis=5000)
        _logger_provider.shutdown()
        _logger_provider = None
    if _provider is not None:
        _provider.force_flush(timeout_millis=5000)
        _provider.shutdown()
        _provider = None
    if _meter_provider is not None:
        _meter_provider.force_flush(timeout_millis=5000)
        _meter_provider.shutdown()
        _meter_provider = None
