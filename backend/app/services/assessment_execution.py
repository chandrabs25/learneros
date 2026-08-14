"""Deep Assessment Execution module.

Routes submit one typed assessment and receive the learner-facing result. External
I/O lives behind the internal runtime seam so production and tests exercise the
same orchestration interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Literal, Protocol, TypeAlias

from fastapi import HTTPException

from app.assessment_observability import (
    AssessmentStatus,
    assessment_event,
    elapsed_ms,
    new_assessment_id,
)
from app.config import settings
from app.observability import fingerprint


logger = logging.getLogger(__name__)
EVAL_MODEL = settings.FIREWORKS_MODEL
EXERCISE_EVAL_MODEL = "gemini-3.1-pro-preview"


@dataclass(frozen=True)
class WrittenAnswerSubmission:
    section_id: str
    subsection_id: str
    question: str
    answer: str
    kind: Literal["written_answer"] = field(default="written_answer", init=False)


@dataclass(frozen=True)
class MCQSubmission:
    section_id: str
    subsection_id: str
    question: str
    options: dict[str, Any]
    selected: str
    correct_answer: str
    kind: Literal["mcq"] = field(default="mcq", init=False)


@dataclass(frozen=True)
class ExerciseSubmission:
    section_id: str
    exercise_id: str
    problem: str
    answer_mode: Literal["text", "image"]
    answer_text: str | None = None
    answer_images: list[str] | None = None
    kind: Literal["exercise"] = field(default="exercise", init=False)


AssessmentSubmission: TypeAlias = WrittenAnswerSubmission | MCQSubmission | ExerciseSubmission


class AssessmentRuntime(Protocol):
    """Internal seam for request, model, graph, and scheduler adapters."""

    student_id: str | None
    authorization_present: bool
    event_logger: Any

    def enforce_rate_limit(self, **values: Any) -> None: ...

    async def load_context(self, section_id: str) -> dict[str, Any]: ...

    async def create_attempt(self, **values: Any) -> None: ...

    async def generate(self, **values: Any) -> dict[str, Any]: ...

    async def record_evaluation(self, **values: Any) -> None: ...

    async def queue_evidence(self, **values: Any) -> str: ...


def _target_subsection(meta: dict[str, Any], subsection_id: str, section_id: str) -> dict[str, Any]:
    target = next(
        (subsection for subsection in meta["subsections"] if subsection["id"] == subsection_id),
        None,
    )
    if target is None:
        raise HTTPException(
            status_code=400,
            detail=f"subsection_id '{subsection_id}' not found in section '{section_id}'",
        )
    return target


def _concept_prompt(meta: dict[str, Any]) -> tuple[str, str]:
    scope = meta.get("concept_scope", "section")
    heading = (
        "CHAPTER CONCEPT CANDIDATES (used because this section has no direct concepts)"
        if scope == "chapter_fallback"
        else "CONCEPTS DIRECTLY LINKED TO THIS SECTION"
    )
    concept_list = "\n".join(
        f'  - concept_id: "{concept["id"]}", name: "{concept["name"]}"'
        for concept in meta["concepts"]
    ) or "  (no concepts linked)"
    return heading, concept_list


def _validated_evidence(
    raw_value: Any,
    *,
    meta: dict[str, Any],
    source_id: str,
) -> tuple[list[dict[str, Any]], int]:
    raw = raw_value if isinstance(raw_value, list) else []
    valid_concept_ids = {concept["id"] for concept in meta["concepts"]}
    accepted: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        concept_id = item.get("concept_id", "")
        evidence_type = item.get("type", "")
        category = item.get("category", "conceptual")
        if concept_id not in valid_concept_ids:
            continue
        if evidence_type not in ("COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"):
            continue
        if category not in ("conceptual", "mathematical"):
            continue
        accepted.append(
            {
                "concept_id": concept_id,
                "concept_name": item.get("concept_name", ""),
                "type": evidence_type,
                "category": category,
                "content": item.get("content", ""),
                "source_id": source_id,
            }
        )
    return accepted, len(raw)


class AssessmentExecutor:
    """Evaluate typed submissions through one stable interface."""

    def __init__(self, runtime: AssessmentRuntime) -> None:
        self.runtime = runtime
        self._event_logger = getattr(runtime, "event_logger", logger)

    async def execute(self, submission: AssessmentSubmission) -> dict[str, Any]:
        if isinstance(submission, WrittenAnswerSubmission):
            return await self._execute_written(submission)
        if isinstance(submission, MCQSubmission):
            return await self._execute_mcq(submission)
        if isinstance(submission, ExerciseSubmission):
            return await self._execute_exercise(submission)
        raise TypeError(f"Unsupported assessment submission: {type(submission).__name__}")

    def _begin(self, submission: AssessmentSubmission) -> tuple[str, float]:
        started_at = time.monotonic()
        assessment_id = new_assessment_id()
        assessment_event(
            self._event_logger,
            assessment_id,
            AssessmentStatus.RECEIVED,
            assessment_kind=submission.kind,
            section_id=submission.section_id,
            authenticated=self.runtime.student_id is not None,
            student_fingerprint=(
                fingerprint(self.runtime.student_id) if self.runtime.student_id else "anonymous"
            ),
        )
        return assessment_id, started_at

    async def _load_context(
        self,
        submission: AssessmentSubmission,
        assessment_id: str,
    ) -> dict[str, Any]:
        started_at = time.monotonic()
        meta = await self.runtime.load_context(submission.section_id)
        assessment_event(
            self._event_logger,
            assessment_id,
            AssessmentStatus.CONTEXT_LOADED,
            assessment_kind=submission.kind,
            stage="context_fetch",
            duration_ms=elapsed_ms(started_at),
            result="success",
            concept_count=len(meta["concepts"]),
            concept_scope=meta.get("concept_scope", "section"),
            subsection_count=len(meta["subsections"]),
        )
        return meta

    async def _generate(
        self,
        *,
        submission: AssessmentSubmission,
        assessment_id: str,
        prompt: str,
        model: str,
        operation: str,
        images: list[str] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        started_at = time.monotonic()
        try:
            data = await self.runtime.generate(
                kind=submission.kind,
                prompt=prompt,
                model=model,
                operation=operation,
                retries=2 if submission.kind == "exercise" else 1,
                images=images,
            )
            duration_ms = elapsed_ms(started_at)
            assessment_event(
                self._event_logger,
                assessment_id,
                AssessmentStatus.MODEL_COMPLETED,
                assessment_kind=submission.kind,
                model=model,
                latency_ms=duration_ms,
                duration_ms=duration_ms,
                stage="model",
                result="success",
            )
            return data, False
        except Exception as exc:
            duration_ms = elapsed_ms(started_at)
            assessment_event(
                self._event_logger,
                assessment_id,
                AssessmentStatus.MODEL_FAILED,
                assessment_kind=submission.kind,
                model=model,
                latency_ms=duration_ms,
                duration_ms=duration_ms,
                stage="model",
                result="failure",
                error_type=type(exc).__name__,
                fallback_used=True,
            )
            return self._fallback(submission), True

    @staticmethod
    def _fallback(submission: AssessmentSubmission) -> dict[str, Any]:
        if isinstance(submission, MCQSubmission):
            correct = submission.selected == submission.correct_answer
            return {
                "feedback": (
                    "Correct!"
                    if correct
                    else "That's not quite right. Review the material and try again."
                ),
                "explanation": "",
                "insights": [],
            }
        improvement = (
            "Try providing clearer step-by-step reasoning."
            if isinstance(submission, ExerciseSubmission)
            else "Try providing more detail"
        )
        return {
            "score": 50,
            "grade": "C",
            "feedback": "Could not fully evaluate. Please try again.",
            "strengths": [],
            "improvements": [improvement],
            "model_answer": "",
            "insights": [],
        }

    async def _finish(
        self,
        *,
        submission: AssessmentSubmission,
        assessment_id: str,
        assessment_started_at: float,
        meta: dict[str, Any],
        source_id: str,
        data: dict[str, Any],
        fallback_used: bool,
        evaluation_values: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str]:
        validation_started_at = time.monotonic()
        evidence, candidate_count = _validated_evidence(
            data.get("insights"),
            meta=meta,
            source_id=source_id,
        )
        assessment_event(
            self._event_logger,
            assessment_id,
            AssessmentStatus.OUTPUT_VALIDATED,
            assessment_kind=submission.kind,
            candidate_insight_count=candidate_count,
            accepted_insight_count=len(evidence),
            rejected_insight_count=candidate_count - len(evidence),
            stage="output_validation",
            duration_ms=elapsed_ms(validation_started_at),
            result="success",
        )
        if self.runtime.student_id:
            await self.runtime.record_evaluation(
                assessment_id=assessment_id,
                evaluation_model=(
                    EXERCISE_EVAL_MODEL if submission.kind == "exercise" else EVAL_MODEL
                ),
                fallback_used=fallback_used,
                concept_ids=[item["concept_id"] for item in evidence],
                **evaluation_values,
            )
        persistence_status = await self.runtime.queue_evidence(
            insights=evidence,
            assessment_id=assessment_id,
            assessment_kind=submission.kind,
            assessment_started_at=assessment_started_at,
        )
        return evidence, persistence_status

    async def _execute_written(self, submission: WrittenAnswerSubmission) -> dict[str, Any]:
        assessment_id, started_at = self._begin(submission)
        self.runtime.enforce_rate_limit(
            scope="test_question_evaluation", limit=60, window_seconds=60
        )
        meta = await self._load_context(submission, assessment_id)
        target = _target_subsection(meta, submission.subsection_id, submission.section_id)
        source_id = target["id"]
        if self.runtime.student_id:
            await self.runtime.create_attempt(
                assessment_id=assessment_id,
                assessment_kind=submission.kind,
                section_id=submission.section_id,
                subsection_id=source_id,
                question=submission.question,
                answer_mode="text",
                answer_text=submission.answer,
            )
        heading, concepts = _concept_prompt(meta)
        prompt = f"""You are an expert teacher evaluating a student's answer.

TARGET SUBSECTION CONTENT (primary ground truth):
{target["content"]}

FULL SECTION REFERENCE CONTEXT (definitions and surrounding context only):
{meta["full_text"]}

QUESTION: {submission.question}

STUDENT'S ANSWER: {submission.answer}

{heading}:
{concepts}

─── TASK ───

1. Evaluate the student's answer for accuracy, completeness, and depth.
2. Generate learning insights ONLY for concepts that the QUESTION DIRECTLY
   tests and the ANSWER meaningfully addresses (correctly or incorrectly).

ASSESSMENT SCOPE:
- Judge the answer against the target subsection content.
- Use the full section only to clarify notation, definitions, or surrounding context.
- Do not require facts that appear only in sibling subsections.

CRITICAL RULES FOR INSIGHTS:
- Do NOT create an insight for a concept unless the question specifically
  asks about it AND the student's answer says something about it.
- If a concept is only tangentially related to the question, do NOT include it.
- It is perfectly fine to return an empty insights array if no concepts
  are directly tested.

Insight types:
- COMPETENCY: student demonstrates correct, solid understanding
- PARTIAL_UNDERSTANDING: student has the right idea but misses key details
- MISCONCEPTION: student shows a factually incorrect understanding

Respond in STRICT JSON:
{{
  "score": <number 0-100>,
  "grade": "<A/B/C/D/F>",
  "feedback": "2-3 sentences of constructive feedback",
  "strengths": ["point1", "point2"],
  "improvements": ["point1", "point2"],
  "model_answer": "A brief ideal answer in 2-3 sentences",
  "insights": [
    {{
      "concept_id": "<exact concept_id from the list above>",
      "concept_name": "<concept name>",
      "type": "<COMPETENCY|PARTIAL_UNDERSTANDING|MISCONCEPTION>",
      "category": "conceptual",
      "content": "One sentence describing what the student understood or misunderstood about this concept"
    }}
  ]
}}

Return ONLY valid JSON, no markdown fences, no extra text."""
        data, fallback_used = await self._generate(
            submission=submission,
            assessment_id=assessment_id,
            prompt=prompt,
            model=EVAL_MODEL,
            operation="json_generation",
        )
        evidence, status = await self._finish(
            submission=submission,
            assessment_id=assessment_id,
            assessment_started_at=started_at,
            meta=meta,
            source_id=source_id,
            data=data,
            fallback_used=fallback_used,
            evaluation_values={
                "score": data.get("score"),
                "grade": data.get("grade"),
                "feedback": data.get("feedback"),
                "strengths": data.get("strengths"),
                "improvements": data.get("improvements"),
                "model_answer": data.get("model_answer"),
            },
        )
        return {
            **data,
            "insights": evidence,
            "section_id": submission.section_id,
            "persistence_status": status,
            "assessment_id": assessment_id,
        }

    async def _execute_mcq(self, submission: MCQSubmission) -> dict[str, Any]:
        assessment_id, started_at = self._begin(submission)
        self.runtime.enforce_rate_limit(scope="test_mcq_evaluation", limit=60, window_seconds=60)
        meta = await self._load_context(submission, assessment_id)
        target = _target_subsection(meta, submission.subsection_id, submission.section_id)
        source_id = target["id"]
        if self.runtime.student_id:
            await self.runtime.create_attempt(
                assessment_id=assessment_id,
                assessment_kind=submission.kind,
                section_id=submission.section_id,
                subsection_id=source_id,
                question=submission.question,
                answer_mode="mcq",
                options=submission.options,
                selected_answer=submission.selected,
                correct_answer=submission.correct_answer,
            )
        is_correct = submission.selected == submission.correct_answer
        heading, concepts = _concept_prompt(meta)
        options = "\n".join(f"  {key}: {value}" for key, value in submission.options.items())
        prompt = f"""You are an expert teacher evaluating a student's MCQ answer.

TARGET SUBSECTION CONTENT (primary ground truth):
{target["content"]}

FULL SECTION REFERENCE CONTEXT (definitions and surrounding context only):
{meta["full_text"]}

QUESTION: {submission.question}
OPTIONS:
{options}
CORRECT ANSWER: {submission.correct_answer}: {submission.options.get(submission.correct_answer, '')}
STUDENT SELECTED: {submission.selected}: {submission.options.get(submission.selected, '')}
IS CORRECT: {is_correct}

{heading}:
{concepts}

─── TASK ───

Generate learning insights based on what the student's choice reveals about their understanding.

CRITICAL RULES:
- Judge the answer against the target subsection content.
- Use the full section only to clarify notation, definitions, or surrounding context.
- Do not require facts that appear only in sibling subsections.
- Generate insights ONLY for concepts directly tested by this question.
- If the student answered correctly → COMPETENCY insights.
- If wrong, determine if their choice suggests a MISCONCEPTION or PARTIAL_UNDERSTANDING.
- It is fine to return an empty insights array if no concepts are directly tested.

Insight types:
- COMPETENCY: student picked correct answer, shows solid understanding
- PARTIAL_UNDERSTANDING: student picked a partially reasonable wrong answer
- MISCONCEPTION: student's choice reveals a factually incorrect understanding

Respond in STRICT JSON:
{{
  "feedback": "2-3 sentences of constructive feedback explaining why their choice was right/wrong",
  "explanation": "Brief explanation of the correct answer",
  "insights": [
    {{
      "concept_id": "<exact concept_id from the list above>",
      "concept_name": "<concept name>",
      "type": "<COMPETENCY|PARTIAL_UNDERSTANDING|MISCONCEPTION>",
      "category": "conceptual",
      "content": "One sentence about what the student's choice reveals"
    }}
  ]
}}

Return ONLY valid JSON, no markdown fences, no extra text."""
        data, fallback_used = await self._generate(
            submission=submission,
            assessment_id=assessment_id,
            prompt=prompt,
            model=EVAL_MODEL,
            operation="json_generation",
        )
        evidence, status = await self._finish(
            submission=submission,
            assessment_id=assessment_id,
            assessment_started_at=started_at,
            meta=meta,
            source_id=source_id,
            data=data,
            fallback_used=fallback_used,
            evaluation_values={
                "is_correct": is_correct,
                "feedback": data.get("feedback", ""),
                "explanation": data.get("explanation", ""),
            },
        )
        return {
            "assessment_id": assessment_id,
            "section_id": submission.section_id,
            "is_correct": is_correct,
            "selected": submission.selected,
            "correct_answer": submission.correct_answer,
            "feedback": data.get("feedback", ""),
            "explanation": data.get("explanation", ""),
            "insights": evidence,
            "persistence_status": status,
        }

    async def _execute_exercise(self, submission: ExerciseSubmission) -> dict[str, Any]:
        answer_text = (submission.answer_text or "").strip()
        answer_images = submission.answer_images or []
        if submission.answer_mode == "text" and not answer_text:
            raise HTTPException(status_code=400, detail="answer_text is required for text mode")
        if submission.answer_mode == "image" and not answer_images:
            raise HTTPException(status_code=400, detail="answer_images is required for image mode")

        assessment_id, started_at = self._begin(submission)
        if self.runtime.student_id:
            await self.runtime.create_attempt(
                assessment_id=assessment_id,
                assessment_kind=submission.kind,
                section_id=submission.section_id,
                exercise_id=submission.exercise_id,
                question=submission.problem,
                answer_mode=submission.answer_mode,
                answer_text=answer_text if submission.answer_mode == "text" else None,
                answer_images=answer_images if submission.answer_mode == "image" else None,
            )
        self.runtime.enforce_rate_limit(scope="test_exercise_evaluation", limit=20, window_seconds=60)
        meta = await self._load_context(submission, assessment_id)
        heading, concepts = _concept_prompt(meta)
        answer_block = (
            f"STUDENT ANSWER (TEXT): {answer_text}"
            if submission.answer_mode == "text"
            else f"STUDENT ANSWER: {len(answer_images)} handwritten image(s) attached."
        )
        prompt = f"""You are an expert physics teacher evaluating a student's chapter-end exercise response.

STUDY MATERIAL (ground truth):
{meta["full_text"]}

EXERCISE ID: {submission.exercise_id}
EXERCISE QUESTION:
{submission.problem}

INPUT MODE: {"IMAGE" if submission.answer_mode == "image" else "TEXT"}
{answer_block}

{heading}:
{concepts}

TASK:
1. Evaluate accuracy, completeness, and reasoning quality.
2. If the answer is from image input, read the student's handwritten work from the attached images.
3. Generate insights ONLY for concepts directly tested by this exercise and evidenced in the student's response.
4. It is valid to return an empty insights array if no direct concept signal exists.

Insight types:
- COMPETENCY
- PARTIAL_UNDERSTANDING
- MISCONCEPTION

Respond in STRICT JSON:
{{
  "score": <number 0-100>,
  "grade": "<A/B/C/D/F>",
  "feedback": "2-4 sentences",
  "strengths": ["point1", "point2"],
  "improvements": ["point1", "point2"],
  "model_answer": "A concise ideal answer in 3-6 sentences",
  "insights": [
    {{
      "concept_id": "<exact concept_id from the concept list above>",
      "concept_name": "<concept name>",
      "type": "<COMPETENCY|PARTIAL_UNDERSTANDING|MISCONCEPTION>",
      "category": "<conceptual|mathematical>",
      "content": "One sentence describing what the student understood or misunderstood"
    }}
  ]
}}

Return ONLY valid JSON."""
        data, fallback_used = await self._generate(
            submission=submission,
            assessment_id=assessment_id,
            prompt=prompt,
            model=EXERCISE_EVAL_MODEL,
            operation="exercise_evaluation",
            images=answer_images if submission.answer_mode == "image" else None,
        )
        evidence, status = await self._finish(
            submission=submission,
            assessment_id=assessment_id,
            assessment_started_at=started_at,
            meta=meta,
            source_id=submission.section_id,
            data=data,
            fallback_used=fallback_used,
            evaluation_values={
                "score": data.get("score"),
                "grade": data.get("grade"),
                "feedback": data.get("feedback", ""),
                "strengths": data.get("strengths", []),
                "improvements": data.get("improvements", []),
                "model_answer": data.get("model_answer", ""),
            },
        )
        return {
            "assessment_id": assessment_id,
            "section_id": submission.section_id,
            "exercise_id": submission.exercise_id,
            "model": EXERCISE_EVAL_MODEL,
            "answer_mode": submission.answer_mode,
            "score": data.get("score", 0),
            "grade": data.get("grade", ""),
            "feedback": data.get("feedback", ""),
            "strengths": data.get("strengths", []),
            "improvements": data.get("improvements", []),
            "model_answer": data.get("model_answer", ""),
            "insights": evidence,
            "persistence_status": status,
        }
