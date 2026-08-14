"""
Student Insights API — personalized learning state tracking.

All endpoints require authentication (get_current_user).

Routes:
  GET    /api/students/me/insights                      → Active insights (optional chapter filter)
  GET    /api/students/me/insights/subsection/{subsection_id} → Active insights for a subsection
  GET    /api/students/me/insights/concept/{concept_id} → Full insight log for a concept
  GET    /api/sections/{section_id}/prerequisites-state → Prerequisites + insight states
"""

import json
import logging
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth import get_current_user, CurrentUser
from app.config import settings
from app.database import read_query
from app.services.llm import llm_service
from app.services.assessment_attempts import (
    create_assessment_attempt,
    record_assessment_evaluation,
)
from app.services.learner_evidence import queue_learner_evidence, skip_learner_evidence
from app.observability import trace_event
from app.services import insight_cache
from app.services.mcq import (
    INSIGHT_MCQ_JSON_SCHEMA,
    MCQ_MAX_TOKENS,
    mcq_validation_errors,
    normalize_mcq_options,
)

router = APIRouter(prefix="/api", tags=["insights"])
logger = logging.getLogger(__name__)


def _cache_get(key: str):
    return insight_cache.get(key)


def _cache_set(key: str, payload):
    insight_cache.set(key, payload)


def _embed_text(text: str) -> list[float]:
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="query text is required")
    return llm_service.embed(
        provider="fireworks",
        model=settings.FIREWORKS_EMBEDDING_MODEL,
        text=text,
        operation="insight_search_embedding",
    )


def _llm_json(
    prompt: str,
    model: str | None = None,
    *,
    max_tokens: int | None = None,
    json_schema: dict | None = None,
    schema_name: str = "response",
) -> dict:
    return llm_service.generate_json(
        provider="fireworks",
        model=model or settings.FIREWORKS_MODEL,
        prompt=prompt,
        temperature=0.1,
        timeout=60,
        retries=2,
        operation="insight_action",
        max_tokens=max_tokens,
        json_schema=json_schema,
        schema_name=schema_name,
    )


def _safe_llm_json(prompt: str, *, operation: str, **kwargs) -> dict:
    """Keep provider exception content out of the generic HTTP exception logger."""
    try:
        return _llm_json(prompt, **kwargs)
    except Exception as exc:
        trace_event(
            logger,
            "insight.llm.failed",
            operation=operation,
            provider="fireworks",
            model=settings.FIREWORKS_MODEL,
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="The AI service could not complete this insight action. Please try again.",
        ) from None


def _get_insight_context(student_id: str, insight_id: str) -> dict | None:
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {id: $insight_id, is_active: true})
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (sec:Section)-[:CONTAINS]->(ss:Subsection)
        WHERE src = ss
        RETURN i.id AS id,
               i.type AS type,
               i.category AS category,
               i.content AS content,
               src.id AS source_id,
               coalesce(src.title, sec.title, src.id) AS source_title,
               sec.id AS section_id,
               c.id AS concept_id,
               c.name AS concept_name
        LIMIT 1
        """,
        student_id=student_id,
        insight_id=insight_id,
    )
    return rows[0] if rows else None


# ── GET /api/students/me/insights ─────────────────────────────────────────────

@router.get("/students/me/insights")
async def get_my_insights(
    chapter_id: str | None = Query(default=None, description="Filter to insights about this chapter's sections/concepts"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=200, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    """
    Returns all active insights for the current student.
    Optionally filtered to a chapter (by matching section and concept ids).
    """
    cache_key = f"my_insights|{user.student_id}|{chapter_id or ''}|{page}|{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if chapter_id:
        rows = read_query(
            """
            // Collect section + subsection + concept ids for this chapter
            MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
            OPTIONAL MATCH (sec)-[:CONTAINS]->(ss:Subsection)
            OPTIONAL MATCH (sec)-[:REQUIRES]->(concept:Concept)
            WITH collect(DISTINCT sec.id) + collect(DISTINCT ss.id) AS source_ids,
                 collect(DISTINCT concept.id) AS concept_ids
            WITH [sid IN source_ids WHERE sid IS NOT NULL] AS sids,
                 [cid IN concept_ids WHERE cid IS NOT NULL] AS cids

            // Fetch active insights that touch those nodes
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            WHERE any(sid IN sids WHERE (i)-[:ABOUT_SOURCE]->({id: sid}))
               OR any(cid IN cids WHERE (i)-[:ABOUT_CONCEPT]->(:Concept {id: cid}))
            OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
            OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)

            RETURN i.id         AS id,
                   i.type       AS type,
                   i.category   AS category,
                   i.content    AS content,
                   i.created_at AS created_at,
                   src.id       AS source_id,
                   src.title    AS source_title,
                   c.id         AS concept_id,
                   c.name       AS concept_name
            ORDER BY i.created_at DESC
            SKIP $skip
            LIMIT $limit
            """,
            student_id=user.student_id,
            chapter_id=chapter_id,
            skip=(page - 1) * limit,
            limit=limit,
        )
    else:
        rows = read_query(
            """
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
            OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
            RETURN i.id         AS id,
                   i.type       AS type,
                   i.category   AS category,
                   i.content    AS content,
                   i.created_at AS created_at,
                   src.id       AS source_id,
                   src.title    AS source_title,
                   c.id         AS concept_id,
                   c.name       AS concept_name
            ORDER BY i.created_at DESC
            SKIP $skip
            LIMIT $limit
            """,
            student_id=user.student_id,
            skip=(page - 1) * limit,
            limit=limit,
        )

    _cache_set(cache_key, rows)
    return rows


# ── GET /api/students/me/insights/subsection/{subsection_id} ─────────────────

@router.get("/students/me/insights/subsection/{subsection_id:path}")
async def get_subsection_insights(
    subsection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return active insights linked to a specific subsection for the current student."""
    # This projection must converge immediately after background persistence.
    # A process-local cache can be stale when the write and read hit different workers.
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE (i)-[:ABOUT_SOURCE]->(:Subsection {id: $subsection_id})
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        RETURN i.id         AS id,
               i.type       AS type,
               i.category   AS category,
               i.content    AS content,
               i.created_at AS created_at,
               $subsection_id AS source_id,
               c.id         AS concept_id,
               c.name       AS concept_name
        ORDER BY i.created_at DESC
        """,
        student_id=user.student_id,
        subsection_id=subsection_id,
    )
    return rows


# ── GET /api/students/me/insights/search ──────────────────────────────────────

@router.get("/students/me/insights/search")
async def semantic_search_my_insights(
    query: str = Query(..., description="Natural language query to match relevant active insights"),
    k: int = Query(default=5, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
):
    """Semantic retrieval over the student's active insights using stored embeddings."""
    embedding = _embed_text(query)

    # Preferred: vector index query. Fallback: cosine similarity scan.
    try:
        rows = read_query(
            """
            CALL db.index.vector.queryNodes('insight_embedding_index', $n, $embedding)
            YIELD node, score
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(node)
            WHERE node.is_active = true
            OPTIONAL MATCH (node)-[:ABOUT_SOURCE]->(src)
            OPTIONAL MATCH (node)-[:ABOUT_CONCEPT]->(c:Concept)
            RETURN node.id AS id,
                   node.type AS type,
                   node.category AS category,
                   node.content AS content,
                   node.created_at AS created_at,
                   src.id AS source_id,
                   src.title AS source_title,
                   c.id AS concept_id,
                   c.name AS concept_name,
                   score AS similarity
            ORDER BY score DESC
            LIMIT $k
            """,
            student_id=user.student_id,
            embedding=embedding,
            n=max(k * 4, 20),
            k=k,
        )
    except Exception:
        rows = read_query(
            """
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            WHERE i.embedding IS NOT NULL
            WITH i, vector.similarity.cosine(i.embedding, $embedding) AS score
            OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
            OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
            RETURN i.id AS id,
                   i.type AS type,
                   i.category AS category,
                   i.content AS content,
                   i.created_at AS created_at,
                   src.id AS source_id,
                   src.title AS source_title,
                   c.id AS concept_id,
                   c.name AS concept_name,
                   score AS similarity
            ORDER BY score DESC
            LIMIT $k
            """,
            student_id=user.student_id,
            embedding=embedding,
            k=k,
        )

    return rows


# ── GET /api/students/me/insights/concept/{concept_id} ────────────────────────

@router.get("/students/me/insights/concept/{concept_id:path}")
async def get_concept_insight_log(
    concept_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Full chronological insight log for a specific concept — active AND superseded.
    Used by the knowledge graph sidebar when a concept node is selected.
    """
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight)
              -[:ABOUT_CONCEPT]->(c:Concept {id: $concept_id})
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH (i)-[:SUPERSEDES]->(old:Insight)
        RETURN i.id           AS id,
               i.type         AS type,
               i.category     AS category,
               i.content      AS content,
               i.is_active    AS is_active,
               i.created_at   AS created_at,
               src.id         AS source_id,
               src.title      AS source_title,
               old.id         AS superseded_id
        ORDER BY i.created_at DESC
        """,
        student_id=user.student_id,
        concept_id=concept_id,
    )
    return rows


class InsightMCQEvaluatePayload(BaseModel):
    question: str
    options: dict
    selected: str
    correct_answer: str


@router.post("/students/me/insights/{insight_id}/explain")
async def explain_insight(
    insight_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    ctx = _get_insight_context(user.student_id, insight_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Insight not found or inactive.")

    prompt = f"""You are a tutor helping a student clear a misunderstanding.

INSIGHT TYPE: {ctx["type"]}
CATEGORY: {ctx["category"]}
CONCEPT: {ctx.get("concept_name") or ctx.get("concept_id") or "General"}
SOURCE: {ctx.get("source_title") or ctx.get("source_id") or "Unknown"}
INSIGHT TEXT: {ctx.get("content") or ""}

Respond in strict JSON:
{{
  "explanation": "Clear explanation in 4-8 sentences to correct/strengthen understanding.",
  "key_points": ["point1", "point2", "point3"],
  "quick_check": "One short self-check question"
}}
"""
    data = _safe_llm_json(prompt, operation="insight_explanation")
    return {
        "insight_id": insight_id,
        "explanation": data.get("explanation", ""),
        "key_points": data.get("key_points", []),
        "quick_check": data.get("quick_check", ""),
    }


@router.post("/students/me/insights/{insight_id}/test/mcq")
async def generate_insight_mcq(
    insight_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    ctx = _get_insight_context(user.student_id, insight_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Insight not found or inactive.")

    prompt = f"""Create ONE MCQ targeting this student insight.

INSIGHT TYPE: {ctx["type"]}
CATEGORY: {ctx["category"]}
CONCEPT: {ctx.get("concept_name") or ctx.get("concept_id") or "General"}
SOURCE: {ctx.get("source_title") or ctx.get("source_id") or "Unknown"}
INSIGHT TEXT: {ctx.get("content") or ""}

Return STRICT JSON:
{{
  "question": "Question text",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct_answer": "A or B or C or D",
  "explanation": "Why correct option is correct"
}}

The four choices MUST be nested inside the "options" object. Do not return A,
B, C, or D as top-level JSON keys.
"""
    data = normalize_mcq_options(
        _safe_llm_json(
            prompt,
            operation="insight_mcq_generation",
            max_tokens=MCQ_MAX_TOKENS,
            json_schema=INSIGHT_MCQ_JSON_SCHEMA,
            schema_name="insight_mcq",
        )
    )
    validation_errors = mcq_validation_errors(data)
    if validation_errors:
        trace_event(
            logger,
            "insight_mcq.payload.invalid",
            insight_id=insight_id,
            model=settings.FIREWORKS_MODEL,
            option_count=(
                len(data["options"]) if isinstance(data.get("options"), dict) else 0
            ),
            validation_errors=validation_errors,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to generate a complete MCQ. Please try again.",
        )
    return {
        "insight_id": insight_id,
        "question": data.get("question", ""),
        "options": data.get("options", {}),
        "correct_answer": data.get("correct_answer", "A"),
        "explanation": data.get("explanation", ""),
    }


@router.post("/students/me/insights/{insight_id}/test/mcq/evaluate")
async def evaluate_insight_mcq(
    insight_id: str,
    body: InsightMCQEvaluatePayload,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    assessment_started_at = time.monotonic()
    ctx = _get_insight_context(user.student_id, insight_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Insight not found or inactive.")

    is_correct = body.selected == body.correct_answer
    prompt = f"""Evaluate this insight-focused MCQ attempt.

CONCEPT: {ctx.get("concept_name") or ctx.get("concept_id") or "General"}
ORIGINAL INSIGHT: {ctx.get("content") or ""}
QUESTION: {body.question}
OPTIONS: {json.dumps(body.options)}
CORRECT: {body.correct_answer}
SELECTED: {body.selected}
IS_CORRECT: {is_correct}

Return STRICT JSON:
{{
  "feedback": "2-3 sentence feedback",
  "type": "COMPETENCY or PARTIAL_UNDERSTANDING or MISCONCEPTION",
  "content": "Single sentence new insight content"
}}
"""
    data = _safe_llm_json(prompt, operation="insight_mcq_evaluation")
    new_type = data.get("type", "PARTIAL_UNDERSTANDING")
    if new_type not in ("COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"):
        new_type = "COMPETENCY" if is_correct else "PARTIAL_UNDERSTANDING"
    new_content = data.get("content", "")
    if not isinstance(new_content, str) or not new_content.strip():
        new_content = (
            "Student now demonstrates stronger understanding of this concept."
            if is_correct
            else "Student still has gaps in this concept and needs more targeted practice."
        )

    assessment_id = f"assessment:{uuid.uuid4().hex}"
    section_id = ctx.get("section_id") or ctx.get("source_id") or "unknown"
    source_id = ctx.get("source_id") or section_id
    await run_in_threadpool(
        create_assessment_attempt,
        assessment_id=assessment_id,
        student_id=user.student_id,
        assessment_kind="insight_mcq",
        section_id=section_id,
        subsection_id=source_id if source_id != section_id else None,
        question=body.question,
        answer_mode="mcq",
        options=body.options,
        selected_answer=body.selected,
        correct_answer=body.correct_answer,
    )
    await run_in_threadpool(
        record_assessment_evaluation,
        assessment_id=assessment_id,
        evaluation_model=settings.FIREWORKS_MODEL,
        fallback_used=False,
        concept_ids=[ctx["concept_id"]] if ctx.get("concept_id") else [],
        is_correct=is_correct,
        feedback=data.get("feedback", ""),
    )

    if ctx.get("concept_id"):
        persistence_status = "queued" if await run_in_threadpool(
            queue_learner_evidence,
            user.student_id,
            [{
                "concept_id": ctx["concept_id"],
                "type": new_type,
                "category": ctx.get("category") or "conceptual",
                "content": new_content,
                "source_id": source_id,
            }],
            assessment_id=assessment_id,
            assessment_kind="insight_mcq",
            assessment_started_at=assessment_started_at,
            schedule=background_tasks.add_task,
        ) else "failed_to_queue"
    else:
        await run_in_threadpool(
            skip_learner_evidence,
            assessment_id=assessment_id,
            reason="no_valid_concept",
        )
        persistence_status = "skipped_no_insights"

    return {
        "assessment_id": assessment_id,
        "persistence_status": persistence_status,
        "insight_id": insight_id,
        "is_correct": is_correct,
        "feedback": data.get("feedback", ""),
        "new_insight": {
            "type": new_type,
            "category": ctx.get("category") or "conceptual",
            "content": new_content,
            "concept_id": ctx.get("concept_id"),
            "source_id": ctx.get("source_id"),
        },
    }


# ── GET /api/sections/{section_id}/prerequisites-state ────────────────────────

@router.get("/sections/{section_id:path}/prerequisites-state")
async def get_prerequisites_state(
    section_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Returns prerequisites for a section along with the student's current
    insight state for each. Used before starting a new section to determine
    if remediation or redirection is needed.

    Returns:
      [{ id, type (Section|Concept), title, insight_type, insight_category, insight_content }]
    """
    cache_key = f"prereq_state|{user.student_id}|{section_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    rows = read_query(
        """
        MATCH (sec:Section {id: $section_id})-[:REQUIRES]->(prereq)
        OPTIONAL MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE (i)-[:ABOUT_SOURCE]->(prereq) OR (i)-[:ABOUT_CONCEPT]->(prereq)
        WITH prereq, i
        ORDER BY i.created_at DESC
        WITH prereq, collect(i)[0] AS i
        RETURN prereq.id           AS id,
               labels(prereq)[0]  AS prereq_type,
               coalesce(prereq.title, prereq.name, prereq.id) AS title,
               i.type             AS insight_type,
               i.category         AS insight_category,
               i.content          AS insight_content
        """,
        section_id=section_id,
        student_id=user.student_id,
    )
    _cache_set(cache_key, rows)
    return rows
