import logging
import unittest

import pytest

from app import telemetry
from app.telemetry import _headers, configure_telemetry


class TelemetryTests(unittest.TestCase):
    def test_otlp_headers_are_parsed_and_url_decoded(self):
        self.assertEqual(
            _headers("Authorization=Bearer%20secret,X-Tenant=learneros"),
            {"Authorization": "Bearer secret", "X-Tenant": "learneros"},
        )

    def test_blank_otlp_headers_are_ignored(self):
        self.assertIsNone(_headers("  "))

    def test_disabled_telemetry_is_a_noop(self):
        configure_telemetry()


def test_enabled_telemetry_exports_application_logs_to_derived_otlp_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, *args, **kwargs):
            self.processors: list[object] = []

        def add_span_processor(self, processor: object) -> None:
            self.processors.append(processor)

        def add_log_record_processor(self, processor: object) -> None:
            self.processors.append(processor)

        def force_flush(self, *args, **kwargs) -> None:
            return None

        def shutdown(self) -> None:
            return None

    class FakeLoggingHandler(logging.Handler):
        def __init__(self, *, level: int, logger_provider: object):
            super().__init__(level=level)
            self.logger_provider = logger_provider

    class FakeInstrumentor:
        def instrument(self, **kwargs) -> None:
            return None

    monkeypatch.setattr(telemetry.settings, "OTEL_ENABLED", True)
    monkeypatch.setattr(telemetry.settings, "OTEL_CAPTURE_CONTENT", False)
    monkeypatch.delenv("OPENINFERENCE_HIDE_EMBEDDINGS_TEXT", raising=False)
    monkeypatch.delenv("OPENINFERENCE_HIDE_EMBEDDINGS_VECTORS", raising=False)
    monkeypatch.setattr(
        telemetry.settings,
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "https://otlp-gateway.example/otlp/v1/traces",
    )
    monkeypatch.setattr(telemetry.settings, "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "")
    monkeypatch.setattr(telemetry, "_provider", None)
    monkeypatch.setattr(telemetry, "_meter_provider", None)
    monkeypatch.setattr(telemetry, "_logger_provider", None, raising=False)
    monkeypatch.setattr(telemetry, "TracerProvider", FakeProvider)
    monkeypatch.setattr(telemetry, "MeterProvider", FakeProvider)
    monkeypatch.setattr(telemetry, "LoggerProvider", FakeProvider, raising=False)
    monkeypatch.setattr(telemetry, "LoggingHandler", FakeLoggingHandler, raising=False)
    monkeypatch.setattr(telemetry, "BatchSpanProcessor", lambda exporter: exporter)
    monkeypatch.setattr(
        telemetry,
        "BatchLogRecordProcessor",
        lambda exporter: exporter,
        raising=False,
    )
    monkeypatch.setattr(
        telemetry,
        "PeriodicExportingMetricReader",
        lambda exporter, **kwargs: exporter,
    )
    monkeypatch.setattr(telemetry, "OTLPSpanExporter", lambda **kwargs: object())
    monkeypatch.setattr(telemetry, "OTLPMetricExporter", lambda **kwargs: object())
    monkeypatch.setattr(
        telemetry,
        "OTLPLogExporter",
        lambda **kwargs: captured.setdefault("log_exporter_kwargs", kwargs),
        raising=False,
    )
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", lambda provider: None)
    monkeypatch.setattr(telemetry.metrics, "set_meter_provider", lambda provider: None)
    monkeypatch.setattr(telemetry, "OpenAIInstrumentor", lambda: FakeInstrumentor())

    app_logger = logging.getLogger("app")
    original_handlers = list(app_logger.handlers)
    try:
        configure_telemetry()

        assert captured["log_exporter_kwargs"] == {
            "endpoint": "https://otlp-gateway.example/otlp/v1/logs"
        }
        assert any(
            isinstance(handler, FakeLoggingHandler) for handler in app_logger.handlers
        )
        assert telemetry.os.environ["OPENINFERENCE_HIDE_EMBEDDINGS_TEXT"] == "true"
        assert telemetry.os.environ["OPENINFERENCE_HIDE_EMBEDDINGS_VECTORS"] == "true"
    finally:
        app_logger.handlers[:] = original_handlers


if __name__ == "__main__":
    unittest.main()
