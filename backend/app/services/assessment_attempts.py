"""Durable, privacy-conscious records for production assessment attempts."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.database import write_query

logger = logging.getLogger(__name__)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _run(operation: str, query: str, **params: Any) -> list[dict] | None:
    """Keep observability persistence outside the learner-facing failure path."""
    try:
        return write_query(
            query,
            _query_name=f"assessment_attempt.{operation}",
            **params,
        )
    except Exception:
        logger.exception(
            "Assessment attempt persistence failed",
            extra={"operation": operation, "assessment_id": params.get("assessment_id")},
        )
        return None


def create_assessment_attempt(
    *,
    assessment_id: str,
    student_id: str,
    assessment_kind: str,
    section_id: str,
    subsection_id: str | None = None,
    exercise_id: str | None = None,
    question: str | None = None,
    answer_mode: str | None = None,
    answer_text: str | None = None,
    answer_images: list[str] | None = None,
    options: dict | None = None,
    selected_answer: str | None = None,
    correct_answer: str | None = None,
) -> bool:
    """Create the submission record; image contents are represented only by hashes."""
    images = answer_images or []
    image_hashes = [hashlib.sha256(image.encode("utf-8")).hexdigest() for image in images]
    stored_answer_text = None if answer_mode == "image" else answer_text
    rows = _run(
        "create",
        """
        MATCH (s:Student {id: $student_id})
        MERGE (a:AssessmentAttempt {id: $assessment_id})
        ON CREATE SET a.created_at = datetime()
        SET a.schema_version = 1,
            a.kind = $assessment_kind,
            a.section_id = $section_id,
            a.subsection_id = $subsection_id,
            a.exercise_id = $exercise_id,
            a.question = $question,
            a.answer_mode = $answer_mode,
            a.answer_text = $answer_text,
            a.answer_image_count = $answer_image_count,
            a.answer_image_hashes_json = $answer_image_hashes_json,
            a.options_json = $options_json,
            a.selected_answer = $selected_answer,
            a.correct_answer = $correct_answer,
            a.evaluation_status = 'PENDING',
            a.insight_status = 'NOT_STARTED',
            a.expected_insight_count = 0,
            a.persisted_insight_count = 0,
            a.failed_insight_count = 0,
            a.updated_at = datetime()
        MERGE (s)-[:SUBMITTED]->(a)
        WITH a
        OPTIONAL MATCH (section:Section {id: $section_id})
        OPTIONAL MATCH (subsection:Subsection {id: $subsection_id})
        OPTIONAL MATCH (exercise:Exercise {id: $exercise_id})
        FOREACH (_ IN CASE WHEN section IS NULL THEN [] ELSE [1] END |
            MERGE (a)-[:ABOUT_SECTION]->(section))
        FOREACH (_ IN CASE WHEN subsection IS NULL THEN [] ELSE [1] END |
            MERGE (a)-[:ABOUT_SUBSECTION]->(subsection))
        FOREACH (_ IN CASE WHEN exercise IS NULL THEN [] ELSE [1] END |
            MERGE (a)-[:ABOUT_EXERCISE]->(exercise))
        RETURN a.id AS id
        """,
        assessment_id=assessment_id,
        student_id=student_id,
        assessment_kind=assessment_kind,
        section_id=section_id,
        subsection_id=subsection_id,
        exercise_id=exercise_id,
        question=question,
        answer_mode=answer_mode,
        answer_text=stored_answer_text,
        answer_image_count=len(images),
        answer_image_hashes_json=_json(image_hashes),
        options_json=_json(options or {}),
        selected_answer=selected_answer,
        correct_answer=correct_answer,
    )
    return bool(rows)


def record_assessment_evaluation(
    *,
    assessment_id: str,
    evaluation_model: str,
    fallback_used: bool,
    concept_ids: list[str] | None = None,
    score: float | int | None = None,
    grade: str | None = None,
    is_correct: bool | None = None,
    feedback: str | None = None,
    explanation: str | None = None,
    strengths: list[str] | None = None,
    improvements: list[str] | None = None,
    model_answer: str | None = None,
) -> bool:
    rows = _run(
        "evaluation",
        """
        MATCH (a:AssessmentAttempt {id: $assessment_id})
        SET a.evaluation_status = CASE WHEN $fallback_used THEN 'FALLBACK' ELSE 'SUCCEEDED' END,
            a.evaluation_model = $evaluation_model,
            a.fallback_used = $fallback_used,
            a.score = $score,
            a.grade = $grade,
            a.is_correct = $is_correct,
            a.feedback = $feedback,
            a.explanation = $explanation,
            a.strengths_json = $strengths_json,
            a.improvements_json = $improvements_json,
            a.model_answer = $model_answer,
            a.evaluated_at = datetime(),
            a.updated_at = datetime()
        RETURN a.id AS id
        """,
        assessment_id=assessment_id,
        evaluation_model=evaluation_model,
        fallback_used=fallback_used,
        score=score,
        grade=grade,
        is_correct=is_correct,
        feedback=feedback,
        explanation=explanation,
        strengths_json=_json(strengths or []),
        improvements_json=_json(improvements or []),
        model_answer=model_answer,
    )
    if not rows:
        return False

    unique_concept_ids = sorted({value for value in (concept_ids or []) if value})
    if unique_concept_ids:
        linked = _run(
            "concept_links",
            """
            MATCH (a:AssessmentAttempt {id: $assessment_id})
            UNWIND $concept_ids AS concept_id
            MATCH (concept:Concept {id: concept_id})
            MERGE (a)-[:ASSESSED]->(concept)
            RETURN count(concept) AS linked_count
            """,
            assessment_id=assessment_id,
            concept_ids=unique_concept_ids,
        )
        if linked is None:
            return False
    return True


def mark_assessment_insights_queued(*, assessment_id: str, expected_count: int) -> bool:
    rows = _run(
        "insights_queued",
        """
        MATCH (a:AssessmentAttempt {id: $assessment_id})
        SET a.insight_status = 'QUEUED',
            a.expected_insight_count = $expected_count,
            a.persisted_insight_count = 0,
            a.failed_insight_count = 0,
            a.insights_queued_at = datetime(),
            a.updated_at = datetime()
        RETURN a.id AS id
        """,
        assessment_id=assessment_id,
        expected_count=max(0, expected_count),
    )
    return bool(rows)


def mark_assessment_insights_skipped(*, assessment_id: str, reason: str) -> bool:
    rows = _run(
        "insights_skipped",
        """
        MATCH (a:AssessmentAttempt {id: $assessment_id})
        SET a.insight_status = 'SKIPPED',
            a.insight_skip_reason = $reason,
            a.expected_insight_count = 0,
            a.reconciliation_completed_at = datetime(),
            a.updated_at = datetime()
        RETURN a.id AS id
        """,
        assessment_id=assessment_id,
        reason=reason,
    )
    return bool(rows)


def record_assessment_insight_result(
    *, assessment_id: str, success: bool, error: str | None = None
) -> bool:
    rows = _run(
        "insight_result",
        """
        MATCH (a:AssessmentAttempt {id: $assessment_id})
        SET a.persisted_insight_count = coalesce(a.persisted_insight_count, 0)
                + CASE WHEN $success THEN 1 ELSE 0 END,
            a.failed_insight_count = coalesce(a.failed_insight_count, 0)
                + CASE WHEN $success THEN 0 ELSE 1 END,
            a.last_insight_error = CASE WHEN $success THEN a.last_insight_error ELSE $error END,
            a.updated_at = datetime()
        WITH a,
             coalesce(a.persisted_insight_count, 0) AS persisted,
             coalesce(a.failed_insight_count, 0) AS failed,
             coalesce(a.expected_insight_count, 0) AS expected
        SET a.insight_status = CASE
                WHEN persisted + failed < expected THEN 'PROCESSING'
                WHEN failed = 0 THEN 'COMPLETED'
                WHEN persisted = 0 THEN 'FAILED'
                ELSE 'PARTIAL'
            END,
            a.reconciliation_completed_at = CASE
                WHEN persisted + failed >= expected THEN datetime()
                ELSE a.reconciliation_completed_at
            END
        RETURN a.id AS id
        """,
        assessment_id=assessment_id,
        success=success,
        error=error,
    )
    return bool(rows)
