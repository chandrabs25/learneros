"""Production-path tests for assessment, reconciliation, and insight persistence."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.assessment_observability import AssessmentStatus
from app.auth import CurrentUser, get_optional_user
from app.routers import test as test_router


@pytest.fixture
def section_meta() -> dict[str, Any]:
    return {
        "section_id": "section:work",
        "section_title": "Work",
        "subsections": [
            {
                "id": "subsection:work",
                "title": "Work",
                "content": "Work is force applied through displacement.",
            }
        ],
        "full_text": "Work is force applied through displacement.",
        "concepts": [{"id": "concept:work", "name": "Work"}],
        "key_terms": ["Work"],
    }


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(test_router.router)
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(
        uid="student-1",
        email="student@example.com",
        name="Student One",
        role="student",
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def lifecycle_events(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    def record_event(
        _logger: Any,
        assessment_id: str,
        status: AssessmentStatus | str,
        **fields: Any,
    ) -> None:
        status_value = status.value if isinstance(status, AssessmentStatus) else str(status)
        events.append(
            {"assessment_id": assessment_id, "status": status_value, **fields}
        )

    monkeypatch.setattr(test_router, "assessment_event", record_event)
    return events


@pytest.fixture(autouse=True)
def durable_assessment_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, list[dict[str, Any]]]:
    calls: dict[str, list[dict[str, Any]]] = {
        "created": [],
        "evaluated": [],
        "queued": [],
        "skipped": [],
        "results": [],
    }

    def recorder(name: str):
        def record(**kwargs: Any) -> bool:
            calls[name].append(kwargs)
            return True

        return record

    monkeypatch.setattr(test_router, "create_assessment_attempt", recorder("created"))
    monkeypatch.setattr(test_router, "record_assessment_evaluation", recorder("evaluated"))
    monkeypatch.setattr(test_router, "mark_assessment_insights_queued", recorder("queued"))
    monkeypatch.setattr(test_router, "mark_assessment_insights_skipped", recorder("skipped"))
    monkeypatch.setattr(test_router, "record_assessment_insight_result", recorder("results"))
    return calls


def _disable_route_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
) -> None:
    monkeypatch.setattr(test_router, "enforce_rate_limit", lambda *args, **kwargs: None)

    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return section_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)


def _event_statuses(events: list[dict[str, Any]]) -> list[str]:
    return [event["status"] for event in events]


def _assert_timed_stages(events: list[dict[str, Any]]) -> None:
    timed_events = [event for event in events if "stage" in event]
    assert timed_events
    assert all(
        isinstance(event.get("duration_ms"), (int, float))
        and event["duration_ms"] >= 0
        for event in timed_events
    )
    assert all(
        isinstance(event.get("assessment_kind"), str) for event in timed_events
    )


def test_written_evaluation_runs_real_reconcile_and_persistence_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
    lifecycle_events: list[dict[str, Any]],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    _disable_route_boundaries(monkeypatch, section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *args, **kwargs: {
            "score": 82,
            "grade": "B",
            "feedback": "Good reasoning with one remaining gap.",
            "strengths": ["Identifies work"],
            "improvements": ["Account for direction"],
            "model_answer": "Work is the dot product of force and displacement.",
            "insights": [
                {
                    "concept_id": "concept:work",
                    "concept_name": "Work",
                    "type": "COMPETENCY",
                    "category": "conceptual",
                    "content": "The student correctly relates work to displacement.",
                }
            ],
        },
    )
    monkeypatch.setattr(
        test_router,
        "read_query",
        lambda *args, **kwargs: [
            {
                "id": "insight:old",
                "type": "PARTIAL_UNDERSTANDING",
                "content": "The student knows force matters but misses direction.",
            }
        ],
    )
    monkeypatch.setattr(
        test_router,
        "_generate_reconcile_text",
        lambda _prompt: (
            '{"action":"MERGE","type":"PARTIAL_UNDERSTANDING",'
            '"content":"The student relates work to displacement but still needs direction."}'
        ),
    )
    monkeypatch.setattr(
        test_router,
        "_embed_text_with_fireworks",
        lambda _text, retries=2: [0.1, 0.2, 0.3],
    )
    writes: list[dict[str, Any]] = []

    def record_write(_query: str, **params: Any) -> list[dict[str, str]]:
        writes.append(params)
        return [{"id": "insight:new"}]

    monkeypatch.setattr(test_router, "write_query", record_write)

    response = client.post(
        "/api/sections/section:work/test/evaluate",
        headers={"Authorization": "Bearer test-token"},
        json={
            "question": "How is work related to displacement?",
            "answer": "Work depends on force and displacement.",
            "subsection_id": "subsection:work",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assessment_id"].startswith("assessment:")
    assert payload["persistence_status"] == "queued"
    assert response.headers["cache-control"] == "private, no-store"

    assert len(writes) == 1
    write = writes[0]
    assert write["student_id"] == "student:student-1"
    assert write["assessment_id"] == payload["assessment_id"]
    assert write["concept_id"] == "concept:work"
    assert write["source_id"] == "subsection:work"
    assert write["type"] == "PARTIAL_UNDERSTANDING"
    assert write["content"].endswith("still needs direction.")
    assert write["embedding"] == [0.1, 0.2, 0.3]

    assert durable_assessment_calls["created"][0]["assessment_id"] == payload["assessment_id"]
    assert durable_assessment_calls["evaluated"][0]["score"] == 82
    assert durable_assessment_calls["queued"][0]["expected_count"] == 1
    assert durable_assessment_calls["results"] == [
        {"assessment_id": payload["assessment_id"], "success": True}
    ]

    assert _event_statuses(lifecycle_events) == [
        "received",
        "context_loaded",
        "model_completed",
        "output_validated",
        "persistence_queued",
        "request_completed",
        "persistence_started",
        "db_read_completed",
        "reconciled",
        "embedded",
        "persisted",
        "persistence_attempt_completed",
        "persistence_completed",
        "assessment_completed",
    ]
    _assert_timed_stages(lifecycle_events)
    assert {event["assessment_id"] for event in lifecycle_events} == {
        payload["assessment_id"]
    }
    forbidden_content_keys = {"question", "answer", "content", "prompt", "response"}
    assert all(not forbidden_content_keys.intersection(event) for event in lifecycle_events)


def test_written_evaluation_model_failure_returns_safe_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
    lifecycle_events: list[dict[str, Any]],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    _disable_route_boundaries(monkeypatch, section_meta)

    def fail_model(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(test_router, "_generate_json_with_retry", fail_model)
    monkeypatch.setattr(
        test_router,
        "write_query",
        lambda *args, **kwargs: pytest.fail("fallback must not write an insight"),
    )

    response = client.post(
        "/api/sections/section:work/test/evaluate",
        headers={"Authorization": "Bearer test-token"},
        json={
            "question": "Define work.",
            "answer": "I am not sure.",
            "subsection_id": "subsection:work",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] == 50
    assert payload["insights"] == []
    assert payload["persistence_status"] == "skipped_no_insights"
    assert _event_statuses(lifecycle_events) == [
        "received",
        "context_loaded",
        "model_failed",
        "output_validated",
        "persistence_skipped",
        "request_completed",
    ]
    _assert_timed_stages(lifecycle_events)
    model_failure_event = next(
        event for event in lifecycle_events if event["status"] == "model_failed"
    )
    assert model_failure_event["fallback_used"] is True
    assert durable_assessment_calls["created"]
    assert durable_assessment_calls["evaluated"][0]["fallback_used"] is True
    assert durable_assessment_calls["skipped"][0]["reason"] == "no_valid_insights"


def test_mcq_rejects_unlinked_and_invalid_insights_before_persistence(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
    lifecycle_events: list[dict[str, Any]],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    _disable_route_boundaries(monkeypatch, section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *args, **kwargs: {
            "feedback": "Review the definition of work.",
            "explanation": "Work depends on force and displacement.",
            "insights": [
                {
                    "concept_id": "concept:work",
                    "type": "NOT_A_REAL_TYPE",
                    "category": "conceptual",
                    "content": "Invalid type.",
                },
                {
                    "concept_id": "concept:not-linked",
                    "type": "MISCONCEPTION",
                    "category": "conceptual",
                    "content": "Unlinked concept.",
                },
                "not-an-object",
            ],
        },
    )
    monkeypatch.setattr(
        test_router,
        "write_query",
        lambda *args, **kwargs: pytest.fail("rejected insights must not be persisted"),
    )

    response = client.post(
        "/api/sections/section:work/test/mcq/evaluate",
        headers={"Authorization": "Bearer test-token"},
        json={
            "question": "Which expression represents work?",
            "options": {"A": "F d", "B": "F / d", "C": "F + d", "D": "d / F"},
            "selected": "B",
            "correct_answer": "A",
            "subsection_id": "subsection:work",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_correct"] is False
    assert payload["insights"] == []
    assert payload["persistence_status"] == "skipped_no_insights"
    validation_event = next(
        event for event in lifecycle_events if event["status"] == "output_validated"
    )
    assert validation_event["candidate_insight_count"] == 3
    assert validation_event["accepted_insight_count"] == 0
    assert validation_event["rejected_insight_count"] == 3
    assert durable_assessment_calls["created"][0]["assessment_kind"] == "mcq"
    assert durable_assessment_calls["evaluated"][0]["is_correct"] is False
    assert durable_assessment_calls["skipped"][0]["reason"] == "no_valid_insights"
    _assert_timed_stages(lifecycle_events)


def test_invalid_exercise_input_creates_no_assessment_lifecycle(
    client: TestClient,
    lifecycle_events: list[dict[str, Any]],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    response = client.post(
        "/api/sections/section:work/test/exercises/evaluate",
        headers={"Authorization": "Bearer test-token"},
        json={
            "exercise_id": "exercise:1",
            "problem": "Calculate the work done.",
            "answer_mode": "text",
            "answer_text": "   ",
        },
    )

    assert response.status_code == 400
    assert lifecycle_events == []
    assert all(not calls for calls in durable_assessment_calls.values())


def test_background_persistence_reports_retry_then_terminal_dead_letter(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle_events: list[dict[str, Any]],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    attempts: list[int] = []

    def fail_persistence(*args: Any, **kwargs: Any) -> None:
        attempts.append(1)
        raise RuntimeError("database unavailable")

    dead_letters: list[dict[str, Any]] = []
    monkeypatch.setattr(test_router, "_persist_insight", fail_persistence)
    monkeypatch.setattr(
        test_router,
        "_record_persistence_failure",
        lambda student_id, ins, error, **kwargs: dead_letters.append(
            {
                "student_id": student_id,
                "insight": ins,
                "error": error,
                **kwargs,
            }
        ),
    )
    insight = {
        "concept_id": "concept:work",
        "source_id": "subsection:work",
        "category": "conceptual",
        "type": "MISCONCEPTION",
        "content": "The student confuses work and force.",
    }

    test_router._persist_insight_safe(
        "student:student-1",
        insight,
        assessment_id="assessment:test",
        assessment_kind="written_answer",
        assessment_started_at=time.monotonic(),
        queued_at=time.monotonic(),
        insight_index=1,
        insight_total=1,
    )

    assert len(attempts) == 2
    assert _event_statuses(lifecycle_events) == [
        "persistence_started",
        "persistence_retry",
        "persistence_failed",
        "persistence_completed",
        "assessment_completed",
    ]
    _assert_timed_stages(lifecycle_events)
    retry_event = next(
        event for event in lifecycle_events if event["status"] == "persistence_retry"
    )
    assert retry_event["failed_attempt"] == 1
    assert retry_event["next_attempt"] == 2
    assert dead_letters[0]["assessment_id"] == "assessment:test"
    assert dead_letters[0]["assessment_kind"] == "written_answer"
    assert durable_assessment_calls["results"] == [
        {
            "assessment_id": "assessment:test",
            "success": False,
            "error": "database unavailable",
        }
    ]


def test_persistence_rejects_database_write_without_created_record(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle_events: list[dict[str, Any]],
) -> None:
    monkeypatch.setattr(test_router, "read_query", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        test_router,
        "_embed_text_with_fireworks",
        lambda _text, retries=2: [0.1, 0.2],
    )
    monkeypatch.setattr(test_router, "write_query", lambda *args, **kwargs: [])
    insight = {
        "concept_id": "concept:work",
        "source_id": "subsection:work",
        "category": "conceptual",
        "type": "COMPETENCY",
        "content": "The student understands work.",
    }

    with pytest.raises(RuntimeError, match="without creating a record"):
        test_router._persist_insight(
            "student:student-1",
            insight,
            assessment_id="assessment:test",
            assessment_kind="written_answer",
            insight_index=1,
            insight_total=1,
        )

    assert _event_statuses(lifecycle_events) == [
        "db_read_completed",
        "reconciled",
        "embedded",
        "invariant_failed",
    ]
    _assert_timed_stages(lifecycle_events)
    assert lifecycle_events[-1]["reason"] == "insight_create_returned_no_rows"
