"""Tests for privacy-safe assessment lifecycle logging and tracing."""

from __future__ import annotations

from typing import Any

from app import assessment_observability
from app.assessment_observability import AssessmentStatus


class RecordingSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.events: list[tuple[str, dict[str, Any]]] = []

    def is_recording(self) -> bool:
        return True

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any]) -> None:
        self.events.append((name, attributes))


class RecordingTrace:
    def __init__(self, span: RecordingSpan) -> None:
        self.span = span

    def get_current_span(self) -> RecordingSpan:
        return self.span


class RecordingHistogram:
    def __init__(self) -> None:
        self.records: list[tuple[float, dict[str, str]]] = []

    def record(self, value: float, attributes: dict[str, str]) -> None:
        self.records.append((value, attributes))


class RecordingMeter:
    def __init__(self, histogram: RecordingHistogram) -> None:
        self.histogram = histogram

    def create_histogram(self, *args: Any, **kwargs: Any) -> RecordingHistogram:
        return self.histogram


class RecordingMetrics:
    def __init__(self, histogram: RecordingHistogram) -> None:
        self.meter = RecordingMeter(histogram)

    def get_meter(self, *args: Any, **kwargs: Any) -> RecordingMeter:
        return self.meter


def test_assessment_event_emits_structured_log_and_scalar_span_fields(monkeypatch) -> None:
    logged: list[tuple[str, dict[str, Any]]] = []
    span = RecordingSpan()
    monkeypatch.setattr(
        assessment_observability,
        "trace_event",
        lambda _logger, name, **fields: logged.append((name, fields)),
    )
    monkeypatch.setattr(assessment_observability, "trace", RecordingTrace(span))

    assessment_observability.assessment_event(
        object(),
        "assessment:test",
        AssessmentStatus.OUTPUT_VALIDATED,
        accepted_insight_count=2,
        internal_details=["not", "a", "span", "attribute"],
    )

    assert logged == [
        (
            "assessment.lifecycle",
            {
                "assessment_id": "assessment:test",
                "status": "output_validated",
                "accepted_insight_count": 2,
                "internal_details": ["not", "a", "span", "attribute"],
            },
        )
    ]
    assert span.attributes == {
        "assessment.id": "assessment:test",
        "assessment.status": "output_validated",
    }
    assert span.events == [
        (
            "assessment.lifecycle",
            {
                "assessment_id": "assessment:test",
                "status": "output_validated",
                "accepted_insight_count": 2,
            },
        )
    ]


def test_new_assessment_ids_are_opaque_and_unique() -> None:
    first = assessment_observability.new_assessment_id()
    second = assessment_observability.new_assessment_id()

    assert first.startswith("assessment:")
    assert second.startswith("assessment:")
    assert first != second
    assert len(first.removeprefix("assessment:")) == 32


def test_elapsed_ms_is_nonnegative() -> None:
    assert assessment_observability.elapsed_ms(assessment_observability.time.monotonic()) >= 0


def test_duration_metric_uses_only_bounded_cardinality_attributes(monkeypatch) -> None:
    histogram = RecordingHistogram()
    span = RecordingSpan()
    monkeypatch.setattr(
        assessment_observability,
        "metrics",
        RecordingMetrics(histogram),
    )
    monkeypatch.setattr(assessment_observability, "_duration_histogram", None)
    monkeypatch.setattr(assessment_observability, "trace", RecordingTrace(span))
    monkeypatch.setattr(
        assessment_observability,
        "trace_event",
        lambda *args, **kwargs: None,
    )

    assessment_observability.assessment_event(
        object(),
        "assessment:private-id",
        AssessmentStatus.MODEL_COMPLETED,
        duration_ms=125.5,
        stage="model",
        assessment_kind="written_answer",
        result="success",
        model="gemini-3.1-pro-preview",
        concept_id="concept:high-cardinality",
        student_id="student:private",
    )

    assert histogram.records == [
        (
            125.5,
            {
                "assessment.stage": "model",
                "assessment.kind": "written_answer",
                "assessment.result": "success",
                "gen_ai.request.model": "gemini-3.1-pro-preview",
            },
        )
    ]
