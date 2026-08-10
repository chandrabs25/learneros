"""Regression tests for explicit, one-time graph identity provisioning."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.auth import CurrentIdentity
from app.routers import auth as auth_router


def test_student_provisioning_uses_create_only_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_write(query: str, **params: Any) -> list[dict[str, str]]:
        captured["query"] = query
        captured["params"] = params
        return [{"id": "student:user-1"}]

    monkeypatch.setattr(auth_router, "async_write_query", fake_write)
    identity = CurrentIdentity("user-1", "learner@example.com", "Learner", "student")

    result = asyncio.run(auth_router.provision_me(identity))

    assert result == {"status": "ok", "provisioned": True, "role": "student"}
    assert "ON CREATE SET" in captured["query"]
    assert "ON MATCH SET" not in captured["query"]
    assert captured["params"]["_query_name"] == "student.provision"


def test_non_student_provisioning_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_write(*_args: Any, **_kwargs: Any) -> list[dict]:
        pytest.fail("non-student identities must not create Student nodes")

    monkeypatch.setattr(auth_router, "async_write_query", fail_write)
    identity = CurrentIdentity("teacher-1", None, "Teacher", "teacher")

    result = asyncio.run(auth_router.provision_me(identity))

    assert result == {"status": "ok", "provisioned": False, "role": "teacher"}
