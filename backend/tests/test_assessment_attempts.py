"""Tests for durable production assessment-attempt persistence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from app.services import assessment_attempts


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def record_write(query: str, **params: Any) -> list[dict[str, Any]]:
        calls.append({"query": query, "params": params})
        return [{"id": params.get("assessment_id", "assessment:test")}]

    monkeypatch.setattr(assessment_attempts, "write_query", record_write)
    return calls


def test_text_attempt_stores_submission_and_scope(writes: list[dict[str, Any]]) -> None:
    created = assessment_attempts.create_assessment_attempt(
        assessment_id="assessment:text",
        student_id="student:1",
        assessment_kind="written_answer",
        section_id="section:1",
        subsection_id="subsection:1",
        question="Explain work.",
        answer_mode="text",
        answer_text="Work transfers energy.",
    )

    assert created is True
    params = writes[0]["params"]
    assert params["answer_text"] == "Work transfers energy."
    assert params["answer_image_count"] == 0
    assert json.loads(params["answer_image_hashes_json"]) == []
    assert "SUBMITTED" in writes[0]["query"]
    assert "ABOUT_SUBSECTION" in writes[0]["query"]


def test_image_attempt_stores_only_hashes_not_raw_images(
    writes: list[dict[str, Any]],
) -> None:
    image = "data:image/png;base64,secret-image-payload"

    created = assessment_attempts.create_assessment_attempt(
        assessment_id="assessment:image",
        student_id="student:1",
        assessment_kind="chapter_exercise",
        section_id="section:1",
        exercise_id="exercise:1",
        question="Solve the exercise.",
        answer_mode="image",
        answer_text="must not be stored",
        answer_images=[image],
    )

    assert created is True
    params = writes[0]["params"]
    assert params["answer_text"] is None
    assert params["answer_image_count"] == 1
    assert json.loads(params["answer_image_hashes_json"]) == [
        hashlib.sha256(image.encode("utf-8")).hexdigest()
    ]
    assert image not in json.dumps(params)


def test_evaluation_is_recorded_and_linked_to_unique_concepts(
    writes: list[dict[str, Any]],
) -> None:
    recorded = assessment_attempts.record_assessment_evaluation(
        assessment_id="assessment:1",
        evaluation_model="model:test",
        fallback_used=False,
        score=88,
        grade="A",
        feedback="Good answer.",
        strengths=["Reasoning"],
        improvements=["Units"],
        concept_ids=["concept:b", "concept:a", "concept:a", ""],
    )

    assert recorded is True
    assert len(writes) == 2
    assert writes[0]["params"]["score"] == 88
    assert json.loads(writes[0]["params"]["strengths_json"]) == ["Reasoning"]
    assert writes[1]["params"]["concept_ids"] == ["concept:a", "concept:b"]
    assert "ASSESSED" in writes[1]["query"]


def test_insight_lifecycle_writes_queued_skipped_and_result_states(
    writes: list[dict[str, Any]],
) -> None:
    assert assessment_attempts.mark_assessment_insights_queued(
        assessment_id="assessment:1", expected_count=2
    )
    assert assessment_attempts.record_assessment_insight_result(
        assessment_id="assessment:1", success=True
    )
    assert assessment_attempts.record_assessment_insight_result(
        assessment_id="assessment:1", success=False, error="write failed"
    )
    assert assessment_attempts.mark_assessment_insights_skipped(
        assessment_id="assessment:2", reason="no_valid_insights"
    )

    assert len(writes) == 4
    assert writes[0]["params"]["expected_count"] == 2
    assert writes[1]["params"]["success"] is True
    assert writes[2]["params"]["error"] == "write failed"
    assert writes[3]["params"]["reason"] == "no_valid_insights"


def test_database_failure_does_not_break_learner_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_write(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(assessment_attempts, "write_query", fail_write)

    assert assessment_attempts.create_assessment_attempt(
        assessment_id="assessment:failure",
        student_id="student:1",
        assessment_kind="mcq",
        section_id="section:1",
    ) is False
