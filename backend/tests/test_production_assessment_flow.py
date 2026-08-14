"""Production-path tests for assessment, reconciliation, and insight persistence."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.assessment_observability import AssessmentStatus
from app.auth import CurrentUser, get_current_user, get_optional_user
from app.routers import test as test_router
from app.services import assessment_execution, learner_evidence


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
    current_user = CurrentUser(
        uid="student-1",
        email="student@example.com",
        name="Student One",
        role="student",
    )
    app.dependency_overrides[get_optional_user] = lambda: current_user
    app.dependency_overrides[get_current_user] = lambda: current_user
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
    monkeypatch.setattr(assessment_execution, "assessment_event", record_event)
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "emit_event",
        record_event,
    )
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

    def queue(
        student_id: str,
        evidence_items: list[dict[str, Any]],
        *,
        assessment_id: str,
        assessment_kind: str,
        assessment_started_at: float | None = None,
        schedule: Any,
    ) -> bool:
        calls["queued"].append(
            {"assessment_id": assessment_id, "expected_count": len(evidence_items)}
        )
        for index, _evidence in enumerate(evidence_items, start=1):
            schedule(learner_evidence.process_learner_evidence_job, f"job:{index}")
        return True

    def skip(**kwargs: Any) -> bool:
        calls["skipped"].append(kwargs)
        return True

    def record_result(**kwargs: Any) -> dict[str, Any]:
        calls["results"].append(kwargs)
        return {"insight_status": "COMPLETED" if kwargs["success"] else "FAILED"}

    monkeypatch.setattr(test_router, "queue_learner_evidence", queue)
    monkeypatch.setattr(test_router, "skip_learner_evidence", skip)
    monkeypatch.setattr(
        learner_evidence,
        "process_learner_evidence_job",
        lambda _job_id: True,
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "record_result",
        record_result,
    )
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


def test_assessment_status_route_returns_owned_terminal_state(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        test_router,
        "get_assessment_attempt_status",
        lambda **_kwargs: {
            "assessment_id": "assessment:1",
            "insight_status": "COMPLETED",
            "expected_insight_count": 1,
            "persisted_insight_count": 1,
            "failed_insight_count": 0,
        },
    )

    response = client.get("/api/assessment-attempts/assessment:1/status")

    assert response.status_code == 200
    assert response.json()["insight_status"] == "COMPLETED"
    assert response.headers["cache-control"] == "private, no-store"


def test_written_evaluation_queues_validated_durable_evidence_job(
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
        learner_evidence.learner_evidence_persistence.adapters,
        "read",
        lambda *args, **kwargs: [
            {
                "id": "insight:old",
                "type": "PARTIAL_UNDERSTANDING",
                "content": "The student knows force matters but misses direction.",
            }
        ],
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "reconcile_text",
        lambda _prompt: (
            '{"action":"MERGE","type":"PARTIAL_UNDERSTANDING",'
            '"content":"The student relates work to displacement but still needs direction."}'
        ),
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "embed",
        lambda _text: [0.1, 0.2, 0.3],
    )
    writes: list[dict[str, Any]] = []

    def record_write(_query: str, **params: Any) -> list[dict[str, str]]:
        writes.append(params)
        return [{"id": "insight:new"}]

    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
        record_write,
    )

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

    assert writes == []

    assert durable_assessment_calls["created"][0]["assessment_id"] == payload["assessment_id"]
    assert durable_assessment_calls["evaluated"][0]["score"] == 82
    assert durable_assessment_calls["queued"][0]["expected_count"] == 1
    assert durable_assessment_calls["results"] == []

    assert _event_statuses(lifecycle_events) == [
        "received",
        "context_loaded",
        "model_completed",
        "output_validated",
        "persistence_queued",
        "request_completed",
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
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
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


def test_mcq_route_preserves_assessment_execution_contract(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    _disable_route_boundaries(monkeypatch, section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *args, **kwargs: {
            "feedback": "Correct.",
            "explanation": "Work requires displacement.",
            "insights": [],
        },
    )

    response = client.post(
        "/api/sections/section:work/test/mcq/evaluate",
        headers={"Authorization": "Bearer test-token"},
        json={
            "question": "When is work done?",
            "options": {
                "A": "No displacement",
                "B": "With displacement",
                "C": "Never",
                "D": "Always",
            },
            "selected": "B",
            "correct_answer": "B",
            "subsection_id": "subsection:work",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_correct"] is True
    assert payload["explanation"] == "Work requires displacement."
    assert payload["persistence_status"] == "skipped_no_insights"
    assert durable_assessment_calls["created"][0]["answer_mode"] == "mcq"
    assert durable_assessment_calls["evaluated"][0]["is_correct"] is True


def test_exercise_route_preserves_assessment_execution_contract(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
    durable_assessment_calls: dict[str, list[dict[str, Any]]],
) -> None:
    _disable_route_boundaries(monkeypatch, section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *args, **kwargs: {
            "score": 75,
            "grade": "B",
            "feedback": "Mostly correct.",
            "strengths": [],
            "improvements": ["Show units."],
            "model_answer": "W = Fd.",
            "insights": [],
        },
    )

    response = client.post(
        "/api/sections/section:work/test/exercises/evaluate",
        headers={"Authorization": "Bearer test-token"},
        json={
            "exercise_id": "exercise:work:1",
            "problem": "Calculate work.",
            "answer_mode": "text",
            "answer_text": "W = Fd",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] == 75
    assert payload["answer_mode"] == "text"
    assert payload["persistence_status"] == "skipped_no_insights"
    assert durable_assessment_calls["created"][0]["answer_mode"] == "text"
    assert durable_assessment_calls["evaluated"][0]["grade"] == "B"


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
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
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

    def fail_persistence(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        attempts.append(1)
        raise RuntimeError("database unavailable")

    dead_letters: list[dict[str, Any]] = []
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "read",
        fail_persistence,
    )

    def record_dead_letter(_query: str, **params: Any) -> list[dict[str, Any]]:
        dead_letters.append(params)
        return [{"id": params["failure_id"]}]

    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
        record_dead_letter,
    )
    insight = {
        "concept_id": "concept:work",
        "source_id": "subsection:work",
        "category": "conceptual",
        "type": "MISCONCEPTION",
        "content": "The student confuses work and force.",
    }

    learner_evidence._persist_learner_evidence(
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
        "dead_letter_recorded",
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
    assert dead_letters[0]["student_id"] == "student:student-1"
    assert durable_assessment_calls["results"] == [
        {
            "assessment_id": "assessment:test",
            "success": False,
            "error": "RuntimeError",
        }
    ]


def test_successful_assessment_persistence_invalidates_subsection_insight_cache(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle_events: list[dict[str, Any]],
) -> None:
    from app.routers import insights as insights_router

    student_id = "student:student-1"
    subsection_id = "subsection:work"
    cache_key = f"subsection_insights|{student_id}|{subsection_id}"
    insights_router._cache_set(cache_key, [{"id": "insight:stale"}])
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "read",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "embed",
        lambda _text: [0.1, 0.2],
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
        lambda *_args, **params: [{"id": params.get("insight_id", "failure:1")}],
    )

    learner_evidence._persist_learner_evidence(
        student_id,
        {
            "concept_id": "concept:work",
            "source_id": subsection_id,
            "category": "conceptual",
            "type": "COMPETENCY",
            "content": "The student understands work.",
        },
        assessment_id="assessment:test",
        assessment_kind="mcq",
        assessment_started_at=time.monotonic(),
        queued_at=time.monotonic(),
        insight_index=1,
        insight_total=1,
    )

    assert insights_router._cache_get(cache_key) is None


def test_persistence_reports_database_write_without_created_record(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle_events: list[dict[str, Any]],
) -> None:
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "read",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "embed",
        lambda _text: [0.1, 0.2],
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
        lambda *args, **kwargs: (
            [{"id": "failure:1"}]
            if kwargs.get("_query_name") == "insight.dead_letter"
            else []
        ),
    )
    insight = {
        "concept_id": "concept:work",
        "source_id": "subsection:work",
        "category": "conceptual",
        "type": "COMPETENCY",
        "content": "The student understands work.",
    }

    learner_evidence._persist_learner_evidence(
        "student:student-1",
        insight,
        assessment_id="assessment:test",
        assessment_kind="written_answer",
        insight_index=1,
        insight_total=1,
    )

    assert _event_statuses(lifecycle_events) == [
        "persistence_started",
        "db_read_completed",
        "reconciled",
        "embedded",
        "invariant_failed",
        "persistence_retry",
        "db_read_completed",
        "reconciled",
        "embedded",
        "invariant_failed",
        "persistence_failed",
        "dead_letter_recorded",
        "persistence_completed",
        "assessment_completed",
    ]
    _assert_timed_stages(lifecycle_events)
    assert any(
        event.get("reason") == "insight_create_returned_no_rows"
        for event in lifecycle_events
    )


def test_persistence_keeps_new_record_when_no_competing_insight(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle_events: list[dict[str, Any]],
) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "read",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "embed",
        lambda _text: [0.1, 0.2],
    )

    def successful_write(query: str, **params: Any) -> list[dict[str, str]]:
        captured["query"] = query
        return [{"id": params["insight_id"]}]

    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "write",
        successful_write,
    )
    insight = {
        "concept_id": "concept:work",
        "source_id": "subsection:work",
        "category": "conceptual",
        "type": "COMPETENCY",
        "content": "The student understands work.",
    }

    learner_evidence._persist_learner_evidence(
        "student:student-1",
        insight,
        assessment_id="assessment:test",
        assessment_kind="written_answer",
        insight_index=1,
        insight_total=1,
    )

    assert insight["persisted"] is True
    assert "OPTIONAL MATCH" in captured["query"]
    assert "collect(other)" in captured["query"]
    assert "job.status = 'PERSISTED'" in captured["query"]
    assert "RETURN new.id AS id" in captured["query"]
    assert "persisted" in _event_statuses(lifecycle_events)
    assert _event_statuses(lifecycle_events)[-1] == "assessment_completed"
