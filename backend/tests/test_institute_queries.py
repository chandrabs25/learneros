"""Regression tests for institute and dashboard query construction."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.auth import CurrentUser
from app.routers import institutes as institutes_router


def test_list_institutes_passes_query_name_as_driver_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_read(query: str, **params: Any) -> list[dict[str, str]]:
        captured["query"] = query
        captured["params"] = params
        return [{"id": "institute:test", "name": "Test Institute"}]

    monkeypatch.setattr(institutes_router, "async_read_query", fake_read)

    result = asyncio.run(institutes_router.list_institutes())

    assert result == [{"id": "institute:test", "name": "Test Institute"}]
    assert '_query_name="institutes.list"' not in captured["query"]
    assert captured["params"]["_query_name"] == "institutes.list"
    assert "MATCH (i:Institute)" in captured["query"]
    assert "i.logo AS logo" not in captured["query"]
    assert "properties(i)['logo'] AS logo" in captured["query"]


def test_dashboard_passes_grades_query_name_as_driver_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    institutes_router._bootstrap_cache.clear()

    async def fake_profile(_user: CurrentUser) -> dict[str, str]:
        return {"student_id": "student:user-1"}

    async def fake_read(query: str, **params: Any) -> list[dict[str, Any]]:
        captured["query"] = query
        captured["params"] = params
        return [{"grade": 11, "label": "Class 11", "chapter_count": 15}]

    monkeypatch.setattr(institutes_router, "get_student_profile", fake_profile)
    monkeypatch.setattr(institutes_router, "async_read_query", fake_read)
    user = CurrentUser("user-1", "student@example.com", "Student", "student")

    result = asyncio.run(institutes_router.get_student_dashboard_bootstrap(user))

    assert result["grades"][0]["grade"] == 11
    assert '_query_name="dashboard.grades"' not in captured["query"]
    assert captured["params"]["_query_name"] == "dashboard.grades"
    assert "MATCH (t:Textbook)-[:CONTAINS]->(ch:Chapter)" in captured["query"]


def test_student_institute_reads_optional_logo_without_schema_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_read(query: str, **params: Any) -> list[dict[str, Any]]:
        captured["query"] = query
        captured["params"] = params
        return [
            {
                "institute_id": "institute:test",
                "id": "institute:test",
                "name": "Test Institute",
                "logo": None,
            }
        ]

    monkeypatch.setattr(institutes_router, "async_read_query", fake_read)
    user = CurrentUser("user-1", "student@example.com", "Student", "student")

    result = asyncio.run(institutes_router.get_student_institute(user))

    assert result["institute"]["logo"] is None
    assert captured["params"]["_query_name"] == "student.get_institute"
    assert "i.logo AS logo" not in captured["query"]
    assert "properties(i)['logo'] AS logo" in captured["query"]


def test_legacy_student_institute_fallback_reads_optional_logo_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_queries: list[str] = []

    async def fake_read(query: str, **params: Any) -> list[dict[str, Any]]:
        captured_queries.append(query)
        if params["_query_name"] == "student.get_institute":
            return [{"institute_id": "institute:legacy", "id": None}]
        return [{"id": "institute:legacy", "logo": None}]

    monkeypatch.setattr(institutes_router, "async_read_query", fake_read)
    user = CurrentUser("user-1", "student@example.com", "Student", "student")

    result = asyncio.run(institutes_router.get_student_institute(user))

    assert result == {"institute": {"id": "institute:legacy", "logo": None}}
    assert "i.logo AS logo" not in captured_queries[1]
    assert "properties(i)['logo'] AS logo" in captured_queries[1]


def test_student_profile_reads_optional_institute_logo_without_schema_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_read(query: str, **params: Any) -> list[dict[str, Any]]:
        captured["query"] = query
        captured["params"] = params
        return [
            {
                "student_id": "student:user-1",
                "institute_node_id": "institute:test",
                "institute_logo": None,
            }
        ]

    monkeypatch.setattr(institutes_router, "async_read_query", fake_read)
    user = CurrentUser("user-1", "student@example.com", "Student", "student")

    result = asyncio.run(institutes_router.get_student_profile(user))

    assert result["institute"]["logo"] is None
    assert captured["params"]["_query_name"] == "student.profile"
    assert "i.logo AS institute_logo" not in captured["query"]
    assert "properties(i)['logo'] AS institute_logo" in captured["query"]
