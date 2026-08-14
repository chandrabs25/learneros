"""Durability and privacy invariants for Learner Evidence jobs."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from app.services import learner_evidence


def test_queue_is_durable_before_processing_is_scheduled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[dict[str, Any]] = []
    scheduled: list[tuple[Any, str]] = []

    def write(_query: str, **params: Any) -> list[dict[str, Any]]:
        writes.append(params)
        return [{"job_ids": ["evidence_job:1"]}]

    monkeypatch.setattr(learner_evidence.learner_evidence_persistence.adapters, "write", write)

    queued = learner_evidence.queue_learner_evidence(
        "student:1",
        [{"concept_id": "concept:work", "content": "Understands work."}],
        assessment_id="assessment:1",
        assessment_kind="mcq",
        schedule=lambda task, job_id: scheduled.append((task, job_id)),
    )

    assert queued is True
    assert writes[0]["_query_name"] == "learner_evidence.queue_jobs"
    assert scheduled == [(learner_evidence.process_learner_evidence_job, "evidence_job:1")]


def test_unaccounted_persisted_job_recovery_does_not_repeat_llm_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries: list[str] = []
    account_query = ""
    claim_query = ""

    def write(_query: str, **params: Any) -> list[dict[str, Any]]:
        nonlocal account_query, claim_query
        queries.append(params["_query_name"])
        if params["_query_name"] == "learner_evidence.claim_job":
            claim_query = _query
            return [{
                "job_id": "evidence_job:1",
                "assessment_id": "assessment:1",
                "assessment_kind": "mcq",
                "student_id": "student:1",
                "insight_index": 1,
                "insight_total": 1,
                "prior_status": "PERSISTED",
                "success": True,
                "error_type": None,
            }]
        account_query = _query
        return [{"insight_status": "COMPLETED"}]

    monkeypatch.setattr(learner_evidence.learner_evidence_persistence.adapters, "write", write)
    monkeypatch.setattr(
        learner_evidence.learner_evidence_persistence.adapters,
        "embed",
        lambda _text: pytest.fail("recovery must not repeat embedding"),
    )

    assert learner_evidence.process_learner_evidence_job("evidence_job:1") is True
    assert queries == ["learner_evidence.claim_job", "learner_evidence.account_job"]
    assert claim_query.index("SET j.claim_revision") < claim_query.index("WHERE j.status")
    assert "j.claim_token = $claim_token" in claim_query
    assert "claim_token: $claim_token" in account_query
    assert "j.evidence_json = null" in account_query


def test_dead_letter_failure_keeps_durable_job_payload_recoverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[str] = []
    adapters = learner_evidence.learner_evidence_persistence.adapters
    monkeypatch.setattr(
        adapters,
        "read",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    def fail_dead_letter(_query: str, **params: Any) -> list[dict[str, Any]]:
        writes.append(params["_query_name"])
        raise RuntimeError("db still down")

    monkeypatch.setattr(adapters, "write", fail_dead_letter)

    result = learner_evidence.learner_evidence_persistence.persist(
        "student:1",
        {
            "concept_id": "concept:work",
            "source_id": "subsection:work",
            "category": "conceptual",
            "type": "MISCONCEPTION",
            "content": "private evidence",
        },
        context=learner_evidence.PersistenceContext(
            assessment_id="assessment:1",
            job_id="job:1",
            claim_token="claim:1",
        ),
    )

    assert result is False
    assert writes == ["insight.dead_letter"]


def test_stale_claim_is_fenced_before_insight_or_dead_letter_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query_names: list[str] = []
    adapters = learner_evidence.learner_evidence_persistence.adapters
    monkeypatch.setattr(adapters, "read", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(adapters, "embed", lambda _text: [0.1])

    def stale_claim_write(query: str, **params: Any) -> list[dict[str, Any]]:
        query_names.append(params["_query_name"])
        if params["_query_name"] == "insight.persist":
            assert query.index("SET claimed_job.fence_revision") < query.index(
                "WHERE $job_id IS NULL"
            ) < query.index(
                "SET old.is_active"
            )
            assert "claimed_job.claim_token = $claim_token" in query
        if params["_query_name"] == "insight.dead_letter":
            assert query.index("SET claimed_job.fence_revision") < query.index(
                "WHERE $job_id IS NULL"
            ) < query.index("CREATE (f")
            assert "claimed_job.claim_token = $claim_token" in query
        return []  # Neo4j returns no row when another worker owns the token.

    monkeypatch.setattr(adapters, "write", stale_claim_write)
    result = learner_evidence.learner_evidence_persistence.persist(
        "student:1",
        {
            "concept_id": "concept:work",
            "source_id": "subsection:work",
            "category": "conceptual",
            "type": "COMPETENCY",
            "content": "private evidence",
        },
        context=learner_evidence.PersistenceContext(
            assessment_id="assessment:1",
            job_id="job:1",
            claim_token="expired-claim",
        ),
    )

    assert result is False
    assert query_names == ["insight.persist", "insight.persist", "insight.dead_letter"]


def test_provider_exception_content_is_not_logged_or_dead_lettered(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "student answer echoed by provider"
    dead_letters: list[dict[str, Any]] = []

    def fail_read(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError(secret)

    def write(_query: str, **params: Any) -> list[dict[str, Any]]:
        dead_letters.append(params)
        return [{"id": "failure:1"}]

    adapters = learner_evidence.learner_evidence_persistence.adapters
    monkeypatch.setattr(adapters, "read", fail_read)
    monkeypatch.setattr(adapters, "write", write)
    monkeypatch.setattr(
        adapters,
        "record_result",
        lambda **_kwargs: {"insight_status": "FAILED"},
    )

    with caplog.at_level(logging.WARNING):
        learner_evidence._persist_learner_evidence(
            "student:1",
            {
                "concept_id": "concept:work",
                "source_id": "subsection:work",
                "category": "conceptual",
                "type": "MISCONCEPTION",
                "content": "private learner evidence",
            },
            assessment_id="assessment:1",
        )

    assert secret not in caplog.text
    assert dead_letters[-1]["error_type"] == "RuntimeError"
    assert "error" not in dead_letters[-1]
