"""Public-route contract tests for insight-focused MCQ evaluation."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.routers import insights


def test_insight_llm_failure_is_sanitized_before_http_boundary(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = FastAPI()
    app.include_router(insights.router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="student-1",
        email="student@example.com",
        name="Student One",
        role="student",
    )
    monkeypatch.setattr(
        insights,
        "_get_insight_context",
        lambda *_args: {
            "id": "insight:old",
            "type": "MISCONCEPTION",
            "category": "conceptual",
            "content": "private evidence",
            "concept_id": "concept:work",
        },
    )
    secret = "provider echoed the learner answer"
    monkeypatch.setattr(
        insights,
        "_llm_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(secret)),
    )

    with caplog.at_level(logging.ERROR), TestClient(app) as client:
        response = client.post("/api/students/me/insights/insight:old/explain")

    assert response.status_code == 502
    assert secret not in caplog.text
    assert secret not in response.text


def test_insight_mcq_generation_normalizes_flat_nemotron_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(insights.router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="student-1",
        email="student@example.com",
        name="Student One",
        role="student",
    )
    monkeypatch.setattr(
        insights,
        "_get_insight_context",
        lambda _student_id, _insight_id: {
            "id": "insight:old",
            "type": "MISCONCEPTION",
            "category": "conceptual",
            "content": "The student confuses force with work.",
            "source_id": "subsection:work",
            "section_id": "section:work",
            "concept_id": "concept:work",
            "concept_name": "Work",
        },
    )
    monkeypatch.setattr(
        insights,
        "_llm_json",
        lambda _prompt, **_kwargs: {
            "question": "When is mechanical work done?",
            "A": "Whenever force exists",
            "B": "When force causes displacement",
            "C": "Only at rest",
            "D": "Without displacement",
            "correct_answer": "B",
            "explanation": "Work requires displacement.",
        },
    )

    with TestClient(app) as client:
        response = client.post("/api/students/me/insights/insight:old/test/mcq")

    assert response.status_code == 200
    assert response.json()["options"] == {
        "A": "Whenever force exists",
        "B": "When force causes displacement",
        "C": "Only at rest",
        "D": "Without displacement",
    }


def test_insight_mcq_generation_uses_bounded_schema_constrained_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(insights.router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="student-1",
        email="student@example.com",
        name="Student One",
        role="student",
    )
    monkeypatch.setattr(
        insights,
        "_get_insight_context",
        lambda _student_id, _insight_id: {
            "id": "insight:old",
            "type": "MISCONCEPTION",
            "category": "conceptual",
            "content": "The student confuses force with work.",
            "source_id": "subsection:work",
            "section_id": "section:work",
            "concept_id": "concept:work",
            "concept_name": "Work",
        },
    )
    generation_kwargs: dict[str, Any] = {}

    def fake_generate(_prompt: str, **kwargs: Any) -> dict[str, Any]:
        generation_kwargs.update(kwargs)
        return {
            "question": "When is mechanical work done?",
            "options": {
                "A": "Whenever force exists",
                "B": "When force causes displacement",
                "C": "Only at rest",
                "D": "Without displacement",
            },
            "correct_answer": "B",
            "explanation": "Work requires displacement.",
        }

    monkeypatch.setattr(insights, "_llm_json", fake_generate)

    with TestClient(app) as client:
        response = client.post("/api/students/me/insights/insight:old/test/mcq")

    assert response.status_code == 200
    assert generation_kwargs["max_tokens"] == 1200
    assert generation_kwargs["schema_name"] == "insight_mcq"
    assert generation_kwargs["json_schema"]["required"] == [
        "question",
        "options",
        "correct_answer",
        "explanation",
    ]


def test_insight_mcq_returns_feedback_before_persisting_learner_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(insights.router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="student-1",
        email="student@example.com",
        name="Student One",
        role="student",
    )

    monkeypatch.setattr(
        insights,
        "_get_insight_context",
        lambda _student_id, _insight_id: {
            "id": "insight:old",
            "type": "MISCONCEPTION",
            "category": "conceptual",
            "content": "The student confuses force with work.",
            "source_id": "subsection:work",
            "section_id": "section:work",
            "concept_id": "concept:work",
            "concept_name": "Work",
        },
    )
    monkeypatch.setattr(
        insights,
        "_llm_json",
        lambda _prompt: {
            "feedback": "Correct; displacement is required for work.",
            "type": "COMPETENCY",
            "content": "The student now connects work with displacement.",
        },
    )

    events: list[str] = []

    def record_persistence() -> None:
        events.append("persist")

    monkeypatch.setattr(insights, "create_assessment_attempt", lambda **_kwargs: True)
    monkeypatch.setattr(insights, "record_assessment_evaluation", lambda **_kwargs: True)

    def queue_evidence(
        _student_id: str,
        _evidence: list[dict[str, Any]],
        *,
        schedule: Any,
        **_kwargs: Any,
    ) -> bool:
        schedule(record_persistence)
        return True

    monkeypatch.setattr(insights, "queue_learner_evidence", queue_evidence)

    request_payload = json.dumps(
        {
            "question": "When is mechanical work done?",
            "options": {
                "A": "Whenever force exists",
                "B": "When force causes displacement",
                "C": "Only at rest",
                "D": "Without displacement",
            },
            "selected": "B",
            "correct_answer": "B",
        }
    ).encode()
    request_sent = False
    response_body = bytearray()

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {
                "type": "http.request",
                "body": request_payload,
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            events.append("response_start")
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                events.append("response_body")

    asyncio.run(
        app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/students/me/insights/insight:old/test/mcq/evaluate",
                "raw_path": b"/api/students/me/insights/insight:old/test/mcq/evaluate",
                "query_string": b"",
                "root_path": "",
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(request_payload)).encode()),
                ],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
    )

    payload = json.loads(response_body)
    assert payload["is_correct"] is True
    assert payload["persistence_status"] == "queued"
    assert payload["feedback"] == "Correct; displacement is required for work."
    assert payload["new_insight"] == {
        "type": "COMPETENCY",
        "category": "conceptual",
        "content": "The student now connects work with displacement.",
        "concept_id": "concept:work",
        "source_id": "subsection:work",
    }
    assert events.index("response_body") < events.index("persist")
