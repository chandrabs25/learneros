from __future__ import annotations

from typing import Any, Callable

import pytest

from app.routers import tutor
from app.services.llm import ModelTarget


@pytest.mark.parametrize(
    ("responder", "state"),
    [
        (
            tutor._node_respond,
            {
                "user_message": "Explain force.",
                "subsection_context": "Force changes motion.",
                "matched_insights": [],
                "history": [],
            },
        ),
        (
            tutor._node_respond_global,
            {
                "user_message": "Explain force.",
                "matched_insights": [],
                "history": [],
            },
        ),
    ],
)
def test_tutor_generation_caps_completion_length(
    monkeypatch: pytest.MonkeyPatch,
    responder: Callable[[dict[str, Any]], dict[str, Any]],
    state: dict[str, Any],
) -> None:
    captured: dict[str, Any] = {}

    def fake_generate_text(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "Concise answer."

    monkeypatch.setattr(
        tutor,
        "default_generation_targets",
        lambda: [ModelTarget("fireworks", "test-model")],
    )
    monkeypatch.setattr(tutor.llm_service, "generate_text", fake_generate_text)

    result = responder(state)

    assert result["assistant_response"] == "Concise answer."
    assert captured["max_tokens"] == tutor.TUTOR_MAX_TOKENS == 700
