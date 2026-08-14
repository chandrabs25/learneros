"""Regression tests for subsection-scoped assessment context and routing."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import curriculum, test as test_router
from app.services.llm import ModelTarget


class _NoCache:
    def get(self, _key: str) -> None:
        return None

    def set(self, _key: str, _value: dict) -> None:
        return None

    def delete(self, _key: str) -> None:
        return None


@pytest.fixture
def section_meta() -> dict[str, Any]:
    return {
        "section_id": "section:scope",
        "section_title": "Scoped Section",
        "subsections": [
            {
                "id": "subsection:target",
                "title": "Target",
                "content": "TARGET_ONLY_FACT explains the immediate topic.",
            },
            {
                "id": "subsection:sibling",
                "title": "Sibling",
                "content": "SIBLING_REFERENCE_FACT supplies surrounding context.",
            },
        ],
        "full_text": (
            "### Target\nTARGET_ONLY_FACT explains the immediate topic.\n\n"
            "### Sibling\nSIBLING_REFERENCE_FACT supplies surrounding context."
        ),
        "concepts": [{"id": "concept:direct", "name": "Direct Concept"}],
        "concept_scope": "section",
        "key_terms": ["Direct Concept"],
    }


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(test_router.router)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def generation_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(test_router, "enforce_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(test_router, "_generation_cache", _NoCache())
    monkeypatch.setattr(
        test_router,
        "default_generation_targets",
        lambda: [ModelTarget("fireworks", "test-model")],
    )


def test_section_meta_keeps_content_and_builds_chapter_fallback_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_query = ""

    async def fake_read(query: str, **_params: Any) -> list[dict[str, Any]]:
        nonlocal captured_query
        captured_query = query
        return [
            {
                "section_title": "Calculus",
                "subsections": [
                    {
                        "sub_id": "ncert:physics:11:5:5.5:1",
                        "sub_title": "Introduction",
                        "content": "Exact subsection content.",
                    }
                ],
                "concepts": [],
                "concept_scope": "chapter_fallback",
            }
        ]

    monkeypatch.setattr(test_router, "async_read_query", fake_read)

    meta = asyncio.run(test_router._fetch_section_meta("ncert:physics:11:5:5.5"))

    assert meta["subsections"][0]["content"] == "Exact subsection content."
    assert meta["concepts"] == []
    assert meta["concept_scope"] == "chapter_fallback"
    assert "OPTIONAL MATCH (sec)-[:REQUIRES]->(direct:Concept)" in captured_query
    assert "OPTIONAL MATCH (sec)<-[:CONTAINS]-(ch:Chapter)" in captured_query
    assert "OPTIONAL MATCH (ch)-[:CONTAINS]->(chapter_sec:Section)" in captured_query
    assert "WHEN size(direct_concepts) > 0 THEN direct_concepts" in captured_query
    assert "sec2" not in captured_query


@pytest.mark.parametrize(
    ("path_suffix", "response_payload"),
    [
        (
            "question",
            {
                "question": "Explain the target fact.",
                "subsection_id": "subsection:target",
                "hint": "Use the target.",
                "key_terms": ["target"],
            },
        ),
        (
            "mcq",
            {
                "question": "Which statement explains the target fact?",
                "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
                "correct_answer": "A",
                "explanation": "A uses the target content.",
                "subsection_id": "subsection:target",
                "key_terms": ["target"],
            },
        ),
    ],
)
def test_generation_uses_target_content_and_not_concepts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
    path_suffix: str,
    response_payload: dict[str, Any],
) -> None:
    prompts: list[str] = []
    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return section_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)

    def fake_generate(prompt: str, **_kwargs: Any) -> dict[str, Any]:
        prompts.append(prompt)
        return response_payload

    monkeypatch.setattr(test_router, "_generate_json_with_retry", fake_generate)

    response = client.get(
        f"/api/sections/section:scope/test/{path_suffix}",
        params={
            "subsection_id": "subsection:target",
            "variant": 91,
            "concept_id": "concept:must-not-drive-generation",
        },
    )

    assert response.status_code == 200
    assert response.json()["subsection_id"] == "subsection:target"
    assert len(prompts) == 1
    assert "TARGET SUBSECTION CONTENT" in prompts[0]
    assert "TARGET_ONLY_FACT" in prompts[0]
    assert "FULL SECTION REFERENCE CONTEXT" in prompts[0]
    assert "SIBLING_REFERENCE_FACT" in prompts[0]
    assert "concept:direct" not in prompts[0]
    assert "Direct Concept" not in prompts[0]
    assert "must-not-drive-generation" not in prompts[0]


def test_mcq_generation_normalizes_flat_nemotron_options(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
) -> None:
    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return section_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *_args, **_kwargs: {
            "question": "Which option explains the target fact?",
            "A": "First",
            "B": "Second",
            "C": "Third",
            "D": "Fourth",
            "correct_answer": "A",
            "explanation": "The first option uses the target fact.",
            "subsection_id": "subsection:target",
            "key_terms": ["target"],
        },
    )

    response = client.get(
        "/api/sections/section:scope/test/mcq",
        params={"subsection_id": "subsection:target", "variant": 92},
    )

    assert response.status_code == 200
    assert response.json()["options"] == {
        "A": "First",
        "B": "Second",
        "C": "Third",
        "D": "Fourth",
    }


def test_mcq_generation_rejects_incomplete_model_output(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
) -> None:
    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return section_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *_args, **_kwargs: {
            "question": "Which option explains the target fact?",
            "correct_answer": "A",
            "explanation": "Incomplete output.",
            "subsection_id": "subsection:target",
            "key_terms": ["target"],
        },
    )

    response = client.get(
        "/api/sections/section:scope/test/mcq",
        params={"subsection_id": "subsection:target", "variant": 93},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to generate a complete MCQ. Please try again."


def test_written_evaluation_rejects_subsection_outside_section(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
) -> None:
    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return section_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)
    monkeypatch.setattr(
        test_router,
        "_generate_json_with_retry",
        lambda *_args, **_kwargs: pytest.fail("invalid source must fail before evaluation"),
    )

    response = client.post(
        "/api/sections/section:scope/test/evaluate",
        json={
            "question": "Question",
            "answer": "Answer",
            "subsection_id": "subsection:outside",
        },
    )

    assert response.status_code == 400
    assert "not found in section" in response.json()["detail"]


def test_no_concept_section_evaluates_with_empty_insights(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
) -> None:
    prompts: list[str] = []
    no_concept_meta = {
        **section_meta,
        "concepts": [],
        "concept_scope": "chapter_fallback",
        "key_terms": [],
    }
    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return no_concept_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)

    def fake_generate(prompt: str, **_kwargs: Any) -> dict[str, Any]:
        prompts.append(prompt)
        return {
            "score": 90,
            "grade": "A",
            "feedback": "Good answer.",
            "strengths": ["Accurate"],
            "improvements": [],
            "model_answer": "An ideal answer.",
            "insights": [
                {
                    "concept_id": "concept:invented",
                    "concept_name": "Invented",
                    "type": "COMPETENCY",
                    "category": "conceptual",
                    "content": "Must be filtered.",
                }
            ],
        }

    monkeypatch.setattr(test_router, "_generate_json_with_retry", fake_generate)

    response = client.post(
        "/api/sections/section:scope/test/evaluate",
        json={
            "question": "Explain the target fact.",
            "answer": "TARGET_ONLY_FACT explains it.",
            "subsection_id": "subsection:target",
        },
    )

    assert response.status_code == 200
    assert response.json()["insights"] == []
    assert response.json()["persistence_status"] == "skipped_unauthenticated"
    assert "(no concepts linked)" in prompts[0]
    assert "TARGET_ONLY_FACT" in prompts[0]


def test_mcq_evaluation_accepts_insight_from_chapter_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    section_meta: dict[str, Any],
) -> None:
    prompts: list[str] = []
    fallback_meta = {
        **section_meta,
        "concepts": [{"id": "concept:heat", "name": "Heat"}],
        "concept_scope": "chapter_fallback",
        "key_terms": ["Heat"],
    }
    async def fake_section_meta(_section_id: str) -> dict[str, Any]:
        return fallback_meta

    monkeypatch.setattr(test_router, "_fetch_section_meta", fake_section_meta)

    def fake_generate(prompt: str, **_kwargs: Any) -> dict[str, Any]:
        prompts.append(prompt)
        return {
            "feedback": "The selected option correctly applies heat transfer.",
            "explanation": "Heat moves because of a temperature difference.",
            "insights": [
                {
                    "concept_id": "concept:heat",
                    "concept_name": "Heat",
                    "type": "COMPETENCY",
                    "category": "conceptual",
                    "content": "The student correctly identified the heat-transfer mechanism.",
                }
            ],
        }

    monkeypatch.setattr(test_router, "_generate_json_with_retry", fake_generate)

    response = client.post(
        "/api/sections/section:scope/test/mcq/evaluate",
        json={
            "question": "Which option describes heat transfer in this example?",
            "options": {"A": "Transfer", "B": "None", "C": "Other", "D": "Unknown"},
            "selected": "A",
            "correct_answer": "A",
            "subsection_id": "subsection:target",
        },
    )

    assert response.status_code == 200
    assert response.json()["insights"][0]["concept_id"] == "concept:heat"
    assert response.json()["insights"][0]["source_id"] == "subsection:target"
    assert "CHAPTER CONCEPT CANDIDATES" in prompts[0]
    assert 'concept_id: "concept:heat"' in prompts[0]


def test_curriculum_concept_route_does_not_shadow_test_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        curriculum,
        "async_read_query",
        lambda *_args, **_kwargs: pytest.fail("shadow route must not reach curriculum query"),
    )
    app = FastAPI()
    app.include_router(curriculum.router)
    app.include_router(test_router.router)

    with TestClient(app) as route_client:
        response = route_client.get("/api/sections/section:scope/test/concepts")

    assert response.status_code == 404
