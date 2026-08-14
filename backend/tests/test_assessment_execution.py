"""Interface-level tests for the deep Assessment Execution module."""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import settings
from app.services.assessment_execution import (
    AssessmentExecutor,
    ExerciseSubmission,
    MCQSubmission,
    WrittenAnswerSubmission,
)


def section_context() -> dict[str, Any]:
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
        "concept_scope": "section",
        "key_terms": ["Work"],
    }


class FakeRuntime:
    def __init__(self, response: dict[str, Any]) -> None:
        self.student_id = "student:student-1"
        self.authorization_present = True
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def enforce_rate_limit(self, **values: Any) -> None:
        self.calls.append(("rate_limit", values))

    async def load_context(self, section_id: str) -> dict[str, Any]:
        self.calls.append(("context", {"section_id": section_id}))
        return section_context()

    async def create_attempt(self, **values: Any) -> None:
        self.calls.append(("attempt", values))

    async def generate(self, **values: Any) -> dict[str, Any]:
        self.calls.append(("generate", values))
        return self.response

    async def record_evaluation(self, **values: Any) -> None:
        self.calls.append(("evaluation", values))

    async def queue_evidence(self, **values: Any) -> str:
        self.calls.append(("queue", values))
        return "queued"


def test_written_submission_executes_through_one_interface() -> None:
    runtime = FakeRuntime(
        {
            "score": 90,
            "grade": "A",
            "feedback": "Strong answer.",
            "strengths": ["Correct definition"],
            "improvements": [],
            "model_answer": "Work equals force times displacement.",
            "insights": [
                {
                    "concept_id": "concept:work",
                    "concept_name": "Work",
                    "type": "COMPETENCY",
                    "category": "conceptual",
                    "content": "The learner understands work.",
                },
                {
                    "concept_id": "concept:not-in-scope",
                    "type": "MISCONCEPTION",
                    "category": "conceptual",
                    "content": "Must be rejected.",
                },
            ],
        }
    )
    executor = AssessmentExecutor(runtime)

    result = asyncio.run(
        executor.execute(
            WrittenAnswerSubmission(
                section_id="section:work",
                subsection_id="subsection:work",
                question="What is work?",
                answer="Force applied through displacement.",
            )
        )
    )

    assert result["score"] == 90
    assert result["persistence_status"] == "queued"
    assert [row["concept_id"] for row in result["insights"]] == ["concept:work"]
    assert [name for name, _ in runtime.calls] == [
        "rate_limit",
        "context",
        "attempt",
        "generate",
        "evaluation",
        "queue",
    ]


def test_mcq_submission_preserves_immediate_correctness() -> None:
    runtime = FakeRuntime(
        {
            "feedback": "Correct.",
            "explanation": "Work requires displacement.",
            "insights": [],
        }
    )
    executor = AssessmentExecutor(runtime)

    result = asyncio.run(
        executor.execute(
            MCQSubmission(
                section_id="section:work",
                subsection_id="subsection:work",
                question="When is work done?",
                options={"A": "No displacement", "B": "With displacement", "C": "Never", "D": "Always"},
                selected="B",
                correct_answer="B",
            )
        )
    )

    assert result["is_correct"] is True
    assert result["selected"] == "B"
    assert result["correct_answer"] == "B"
    assert result["explanation"] == "Work requires displacement."


def test_exercise_submission_supports_image_mode() -> None:
    runtime = FakeRuntime(
        {
            "score": 75,
            "grade": "B",
            "feedback": "Mostly correct.",
            "strengths": [],
            "improvements": ["Show units."],
            "model_answer": "W = Fd.",
            "insights": [],
        }
    )
    executor = AssessmentExecutor(runtime)

    result = asyncio.run(
        executor.execute(
            ExerciseSubmission(
                section_id="section:work",
                exercise_id="exercise:work:1",
                problem="Calculate work.",
                answer_mode="image",
                answer_images=["data:image/png;base64,abc"],
            )
        )
    )

    assert result["answer_mode"] == "image"
    assert result["score"] == 75
    generated = next(values for name, values in runtime.calls if name == "generate")
    assert generated["images"] == ["data:image/png;base64,abc"]
    assert generated["model"] == settings.FIREWORKS_VISION_MODEL
    assert result["model"] == settings.FIREWORKS_VISION_MODEL


def test_text_exercise_uses_default_text_model() -> None:
    runtime = FakeRuntime(
        {
            "score": 80,
            "grade": "B",
            "feedback": "Correct approach.",
            "strengths": [],
            "improvements": [],
            "model_answer": "W = Fd.",
            "insights": [],
        }
    )
    executor = AssessmentExecutor(runtime)

    result = asyncio.run(
        executor.execute(
            ExerciseSubmission(
                section_id="section:work",
                exercise_id="exercise:work:2",
                problem="Calculate work.",
                answer_mode="text",
                answer_text="W = Fd.",
            )
        )
    )

    generated = next(values for name, values in runtime.calls if name == "generate")
    assert generated["model"] == settings.FIREWORKS_MODEL
    assert result["model"] == settings.FIREWORKS_MODEL
