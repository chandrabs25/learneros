"""Correlation and lifecycle events for production assessment processing."""

from __future__ import annotations

import logging
import time
import uuid
from enum import StrEnum
from typing import Any

from app.observability import trace_event

try:
    from opentelemetry import metrics, trace
except ImportError:  # pragma: no cover - telemetry is an optional deployment feature
    metrics = None  # type: ignore[assignment]
    trace = None  # type: ignore[assignment]


_duration_histogram = None


class AssessmentStatus(StrEnum):
    RECEIVED = "received"
    CONTEXT_LOADED = "context_loaded"
    MODEL_COMPLETED = "model_completed"
    MODEL_FAILED = "model_failed"
    OUTPUT_VALIDATED = "output_validated"
    PERSISTENCE_QUEUED = "persistence_queued"
    PERSISTENCE_SKIPPED = "persistence_skipped"
    REQUEST_COMPLETED = "request_completed"
    PERSISTENCE_STARTED = "persistence_started"
    DB_READ_COMPLETED = "db_read_completed"
    RECONCILED = "reconciled"
    EMBEDDED = "embedded"
    PERSISTED = "persisted"
    PERSISTENCE_ATTEMPT_COMPLETED = "persistence_attempt_completed"
    PERSISTENCE_COMPLETED = "persistence_completed"
    PERSISTENCE_RETRY = "persistence_retry"
    PERSISTENCE_FAILED = "persistence_failed"
    DEAD_LETTER_RECORDED = "dead_letter_recorded"
    ASSESSMENT_COMPLETED = "assessment_completed"
    INVARIANT_FAILED = "invariant_failed"


def new_assessment_id() -> str:
    """Issue an opaque ID that follows one answer through background processing."""
    return f"assessment:{uuid.uuid4().hex}"


def elapsed_ms(started_at: float) -> float:
    """Return monotonic elapsed time in milliseconds."""
    return round((time.monotonic() - started_at) * 1000, 2)


def record_assessment_duration(
    duration_ms: float,
    *,
    stage: str,
    assessment_kind: str,
    result: str = "success",
    model: str | None = None,
) -> None:
    """Record one bounded-cardinality production stage duration."""
    global _duration_histogram
    if metrics is None:
        return
    if _duration_histogram is None:
        meter = metrics.get_meter("learneros.assessment", version="1.0")
        _duration_histogram = meter.create_histogram(
            "learneros.assessment.stage.duration",
            unit="ms",
            description="Duration of a production assessment processing stage",
        )
    attributes = {
        "assessment.stage": stage,
        "assessment.kind": assessment_kind,
        "assessment.result": result,
    }
    if model:
        attributes["gen_ai.request.model"] = model
    _duration_histogram.record(max(float(duration_ms), 0.0), attributes)


def assessment_event(
    logger: logging.Logger,
    assessment_id: str,
    status: AssessmentStatus | str,
    **fields: Any,
) -> None:
    """Write a structured log event and annotate the active OpenTelemetry span."""
    status_value = status.value if isinstance(status, AssessmentStatus) else str(status)
    event_fields = {
        "assessment_id": assessment_id,
        "status": status_value,
        **fields,
    }
    trace_event(logger, "assessment.lifecycle", **event_fields)

    duration_ms = fields.get("duration_ms")
    stage = fields.get("stage")
    assessment_kind = fields.get("assessment_kind")
    if (
        isinstance(duration_ms, (int, float))
        and isinstance(stage, str)
        and isinstance(assessment_kind, str)
    ):
        result = fields.get("result")
        if not isinstance(result, str):
            if status_value.endswith("failed") or status_value == "invariant_failed":
                result = "failure"
            elif status_value == "persistence_retry":
                result = "retry"
            elif status_value.endswith("skipped"):
                result = "skipped"
            else:
                result = "success"
        model = fields.get("model")
        record_assessment_duration(
            duration_ms,
            stage=stage,
            assessment_kind=assessment_kind,
            result=result,
            model=model if isinstance(model, str) else None,
        )

    if trace is None:
        return
    span = trace.get_current_span()
    if not span.is_recording():
        return

    span.set_attribute("assessment.id", assessment_id)
    span.set_attribute("assessment.status", status_value)
    span.add_event(
        "assessment.lifecycle",
        attributes={
            key: value
            for key, value in event_fields.items()
            if isinstance(value, (bool, int, float, str))
        },
    )
