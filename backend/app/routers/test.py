"""
LearnerOS — Test Me Router
─────────────────────────
Generates comprehension questions from section content using configured model providers
and evaluates student answers. Returns structured insight data for
the frontend and persists insights automatically for authenticated users
in the background (guest flow can keep local fallback storage).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Literal
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Response
from fastapi.concurrency import run_in_threadpool
from app.assessment_observability import (
    AssessmentStatus,
    assessment_event,
    elapsed_ms,
)
from app.auth import get_optional_user, CurrentUser

from app.config import settings
from app.database import async_read_query, read_query, write_query
from app.observability import trace_event, trace_exception
from app.services.assessment_attempts import (
    create_assessment_attempt,
    mark_assessment_insights_queued,
    mark_assessment_insights_skipped,
    record_assessment_evaluation,
    record_assessment_insight_result,
)
from app.services.assessment_execution import (
    AssessmentExecutor,
    ExerciseSubmission,
    MCQSubmission,
    WrittenAnswerSubmission,
)
from app.services.generation_cache import build_generation_cache, stable_cache_key
from app.services.insight_cache import invalidate_student as invalidate_student_insight_cache
from app.services.llm import default_generation_targets, llm_service
from app.services.mcq import (
    MCQ_MAX_TOKENS,
    SECTION_MCQ_JSON_SCHEMA,
    mcq_validation_errors,
    normalize_mcq_options,
)
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api", tags=["test"])
logger = logging.getLogger(__name__)

MODEL = settings.FIREWORKS_MODEL
EVAL_MODEL = settings.FIREWORKS_MODEL
EXERCISE_EVAL_MODEL = settings.FIREWORKS_MODEL
GEN_BROWSER_TTL_SECONDS = 300
GEN_EDGE_TTL_SECONDS = 604800
GEN_STALE_WHILE_REVALIDATE_SECONDS = 86400
_generation_cache = build_generation_cache(
    max_entries=settings.GEN_CACHE_MAX_ENTRIES,
    default_ttl_seconds=settings.GEN_CACHE_TTL_SECONDS,
    upstash_url=settings.UPSTASH_REDIS_REST_URL,
    upstash_token=settings.UPSTASH_REDIS_REST_TOKEN,
)


def _generate_reconcile_text(prompt: str) -> str:
    """Generate reconciliation output text via the configured Fireworks model."""
    return _generate_with_fireworks(prompt, model=EVAL_MODEL, temperature=0.1, json_mode=True)


def _generate_with_fireworks(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    return llm_service.generate_text(
        provider="fireworks",
        model=model,
        prompt=prompt,
        system=(
            "Return only valid JSON matching the requested schema."
            if json_mode
            else "You are a helpful educational assistant."
        ),
        temperature=temperature,
        json_mode=json_mode,
        timeout=60,
        operation="test_generation",
    )


def _generate_json_with_retry(
    prompt: str,
    *,
    model: str,
    image_data_urls: list[str] | None = None,
    retries: int = 2,
    operation: str = "json_generation",
    max_tokens: int | None = None,
    json_schema: dict | None = None,
    schema_name: str = "response",
) -> dict:
    return llm_service.generate_json(
        provider="fireworks",
        model=model,
        prompt=prompt,
        images=image_data_urls,
        retries=retries,
        timeout=90 if image_data_urls else 60,
        operation=operation,
        max_tokens=max_tokens,
        json_schema=json_schema,
        schema_name=schema_name,
    )


def _embed_text_with_fireworks(text: str, retries: int = 2) -> list[float]:
    """Create an embedding vector for text using Fireworks embeddings API."""
    return llm_service.embed(
        provider="fireworks",
        model=settings.FIREWORKS_EMBEDDING_MODEL,
        text=text,
        retries=retries,
        operation="insight_embedding",
    )


# ── Helpers ────────────────────────────────────────────────────────────

async def _fetch_section_meta(section_id: str) -> dict:
    """Return section content and the narrowest available assessment concepts."""
    rows = await async_read_query(
        """
        MATCH (sec:Section {id: $section_id})-[:CONTAINS]->(ss:Subsection)
        WITH sec, ss ORDER BY ss.order
        WITH sec,
             collect({sub_id: ss.id, sub_title: ss.title, content: ss.content_text}) AS subsections
        OPTIONAL MATCH (sec)-[:REQUIRES]->(direct:Concept)
        WITH sec, subsections, collect(DISTINCT direct) AS direct_concepts
        OPTIONAL MATCH (sec)<-[:CONTAINS]-(ch:Chapter)
        OPTIONAL MATCH (ch)-[:CONTAINS]->(chapter_sec:Section)-[:REQUIRES]->(chapter_c:Concept)
        WITH sec, subsections, direct_concepts,
             collect(DISTINCT chapter_c) AS chapter_concepts
        WITH sec, subsections,
             CASE
                 WHEN size(direct_concepts) > 0 THEN direct_concepts
                 ELSE chapter_concepts
             END AS assessment_concepts,
             CASE
                 WHEN size(direct_concepts) > 0 THEN "section"
                 ELSE "chapter_fallback"
             END AS concept_scope
        UNWIND (
            CASE
                WHEN size(assessment_concepts) = 0 THEN [null]
                ELSE assessment_concepts
            END
        ) AS c
        WITH sec, subsections, concept_scope,
             collect(DISTINCT CASE WHEN c IS NOT NULL THEN {id: c.id, name: c.name} END) AS raw_concepts
        RETURN sec.title AS section_title,
               subsections,
               concept_scope,
               [x IN raw_concepts WHERE x IS NOT NULL] AS concepts
        """,
        _query_name="assessment.section_context",
        section_id=section_id,
    )
    if not rows or not rows[0].get("subsections"):
        raise HTTPException(status_code=404, detail=f"No content found for {section_id}")

    row = rows[0]
    section_title = row.get("section_title") or section_id
    sub_list = row.get("subsections") or []
    concept_list = row.get("concepts") or []
    concept_scope = row.get("concept_scope") or "section"

    subsections = [
        {
            "id": s["sub_id"],
            "title": s.get("sub_title") or s["sub_id"],
            "content": s.get("content") or "",
        }
        for s in sub_list if s.get("sub_id")
    ]
    text_blocks: list[str] = []
    for s in sub_list:
        title = s.get("sub_title") or ""
        sub_id = s.get("sub_id") or ""
        body = s.get("content") or ""
        header = f"### {title}" if title else "###"
        if sub_id:
            header += f" (subsection_id: {sub_id})"
        text_blocks.append(f"{header}\n{body}")
    full_text = "\n\n".join(text_blocks)

    seen_ids: set[str] = set()
    concepts = []
    for c in concept_list:
        cid = c.get("id")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            concepts.append({"id": cid, "name": (c.get("name") or "").replace("_", " ").title()})
    key_terms = [c["name"] for c in concepts]

    return {
        "section_id": section_id,
        "section_title": section_title,
        "subsections": subsections,
        "full_text": full_text,
        "concepts": concepts,
        "concept_scope": concept_scope,
        "key_terms": key_terms,
    }


def _resolve_target_subsection(meta: dict, subsection_id: str, section_id: str) -> dict:
    """Resolve and validate the subsection used as the assessment source."""
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


def _set_generation_cache_headers(response: Response, cache_status: str, cache_key: str) -> None:
    response.headers["Cache-Control"] = (
        f"public, max-age={GEN_BROWSER_TTL_SECONDS}, "
        f"s-maxage={GEN_EDGE_TTL_SECONDS}, "
        f"stale-while-revalidate={GEN_STALE_WHILE_REVALIDATE_SECONDS}"
    )
    response.headers["CDN-Cache-Control"] = (
        f"public, max-age={GEN_EDGE_TTL_SECONDS}, "
        f"stale-while-revalidate={GEN_STALE_WHILE_REVALIDATE_SECONDS}"
    )
    response.headers["X-Gen-Cache"] = cache_status
    response.headers["X-Gen-Cache-Key"] = cache_key[:16]


def _set_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["CDN-Cache-Control"] = "no-store"


async def _queue_assessment_insights(
    *,
    background_tasks: BackgroundTasks,
    request: Request,
    user: CurrentUser | None,
    insights: list[dict],
    assessment_id: str,
    assessment_kind: str,
    assessment_started_at: float,
) -> str:
    """Queue validated insights and record why persistence did or did not run."""
    queue_started_at = time.monotonic()
    auth_header_present = bool(request.headers.get("authorization"))
    if user and insights:
        insight_total = len(insights)
        await run_in_threadpool(
            mark_assessment_insights_queued,
            assessment_id=assessment_id,
            expected_count=insight_total,
        )
        queued_at = time.monotonic()
        for insight_index, insight in enumerate(insights, start=1):
            background_tasks.add_task(
                _persist_insight_safe,
                user.student_id,
                dict(insight),
                assessment_id=assessment_id,
                insight_index=insight_index,
                insight_total=insight_total,
                assessment_kind=assessment_kind,
                assessment_started_at=assessment_started_at,
                queued_at=queued_at,
            )
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.PERSISTENCE_QUEUED,
            assessment_kind=assessment_kind,
            insight_count=insight_total,
            stage="queue_setup",
            duration_ms=elapsed_ms(queue_started_at),
            result="success",
        )
        persistence_status = "queued"
    else:
        if user:
            reason = "no_valid_insights"
            persistence_status = "skipped_no_insights"
        elif auth_header_present:
            reason = "invalid_or_non_student_auth"
            persistence_status = "skipped_invalid_auth"
        else:
            reason = "unauthenticated"
            persistence_status = "skipped_unauthenticated"
        if user:
            await run_in_threadpool(
                mark_assessment_insights_skipped,
                assessment_id=assessment_id,
                reason=reason,
            )
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.PERSISTENCE_SKIPPED,
            assessment_kind=assessment_kind,
            reason=reason,
            insight_count=len(insights),
            stage="queue_setup",
            duration_ms=elapsed_ms(queue_started_at),
            result="skipped",
        )

    assessment_event(
        logger,
        assessment_id,
        AssessmentStatus.REQUEST_COMPLETED,
        assessment_kind=assessment_kind,
        stage="request_total",
        duration_ms=elapsed_ms(assessment_started_at),
        result="success",
        persistence_status=persistence_status,
    )
    return persistence_status


def _valid_question_payload(data: dict) -> bool:
    return (
        isinstance(data.get("question"), str)
        and isinstance(data.get("subsection_id"), str)
        and isinstance(data.get("hint"), str)
        and isinstance(data.get("key_terms"), list)
    )


def _valid_mcq_payload(data: dict) -> bool:
    return not mcq_validation_errors(
        data,
        require_subsection=True,
        require_key_terms=True,
    )


# ── Generate Question ──────────────────────────────────────────────────
@router.get("/sections/{section_id:path}/test/question")
async def generate_question(
    section_id: str,
    subsection_id: str,
    request: Request,
    response: Response,
    variant: int = 0,
):
    """Generate a question from one subsection, with its section as reference context."""
    trace_event(
        logger,
        "question.request.started",
        section_id=section_id,
        subsection_id=subsection_id,
        variant=variant,
    )
    metadata_started = time.monotonic()
    try:
        meta = await _fetch_section_meta(section_id)
    except Exception as exc:
        trace_exception(
            logger,
            "question.metadata_fetch.failed",
            exc,
            section_id=section_id,
            latency_ms=round((time.monotonic() - metadata_started) * 1000, 2),
        )
        raise
    trace_event(
        logger,
        "question.metadata_fetch.completed",
        section_id=section_id,
        latency_ms=round((time.monotonic() - metadata_started) * 1000, 2),
        subsection_count=len(meta["subsections"]),
        context_chars=len(meta["full_text"]),
    )
    context = meta["full_text"]
    target_sub = _resolve_target_subsection(meta, subsection_id, section_id)
    enforce_rate_limit(request, scope="test_question_generation", limit=30, window_seconds=60)
    generation_targets = default_generation_targets()
    provider = generation_targets[0].provider
    gen_model = generation_targets[0].model

    cache_key = stable_cache_key(
        "test_question:v2",
        {
            "section_id": section_id,
            "subsection_id": target_sub["id"],
            "variant": variant,
            "provider": provider,
            "model": gen_model,
            "fallbacks": [f"{target.provider}:{target.model}" for target in generation_targets[1:]],
            "prompt_version": settings.GEN_PROMPT_VERSION,
        },
    )
    cache_started = time.monotonic()
    cached = _generation_cache.get(cache_key)
    trace_event(
        logger,
        "question.cache_lookup.completed",
        cache_key_fingerprint=cache_key[:16],
        status="hit" if cached is not None else "miss",
        latency_ms=round((time.monotonic() - cache_started) * 1000, 2),
    )
    if cached is not None:
        if not _valid_question_payload(cached):
            _generation_cache.delete(cache_key)
        else:
            _set_generation_cache_headers(response, "HIT", cache_key)
            logger.info(
                "Generation cache hit",
                extra={"endpoint": "test_question", "cache_key": cache_key[:16], "model": gen_model},
            )
            trace_event(
                logger,
                "question.request.completed",
                cache_status="hit",
                section_id=section_id,
                subsection_id=target_sub["id"],
            )
            return cached

    started = time.monotonic()
    prompt = f"""You are an educational assessment AI.

The student is currently studying the subsection "{target_sub["title"]}" 
(subsection_id: "{target_sub["id"]}").

Generate ONE thought-provoking comprehension question that tests deep understanding 
(not simple recall) of THIS SPECIFIC SUBSECTION ONLY. The question must be answerable
from the target subsection content below. It should require the student to explain,
analyze, or connect ideas from this subsection.

TARGET SUBSECTION CONTENT (primary assessment scope):
{target_sub["content"]}

FULL SECTION REFERENCE CONTEXT (definitions and surrounding context only):
{context}

SCOPE RULES:
- Assess only ideas stated in the TARGET SUBSECTION CONTENT.
- Use the full section only to clarify notation, definitions, or context needed to
  understand the target subsection.
- Do not test a sibling subsection or any linked concept that is absent from the
  target subsection.

Respond in STRICT JSON with exactly these keys:
{{
  "question": "The question text",
  "subsection_id": "{target_sub["id"]}",
  "hint": "A brief hint or pro-tip to help the student think about the answer (1-2 sentences)",
  "key_terms": ["term1", "term2", "term3"]
}}

The key_terms should be 3-6 important terms present in the target subsection.
Return ONLY valid JSON, no markdown fences, no extra text."""

    trace_event(
        logger,
        "question.provider.selected",
        provider=provider,
        model=gen_model,
        cache_key_fingerprint=cache_key[:16],
    )
    try:
        data = _generate_json_with_retry(
            prompt,
            model=gen_model,
            retries=2,
            operation="question_generation",
        )
    except Exception as exc:
        trace_exception(
            logger,
            "question.generation.failed",
            exc,
            provider=provider,
            model=gen_model,
            section_id=section_id,
            subsection_id=target_sub["id"],
            cache_key_fingerprint=cache_key[:16],
            latency_ms=round((time.monotonic() - started) * 1000, 2),
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to generate question. The AI returned an invalid response. Please try again.",
        ) from exc

    # The requested subsection is authoritative even if the model echoes another ID.
    subsection_id = target_sub["id"]

    payload = {
        "section_id": section_id,
        "section_title": meta["section_title"],
        "subsection_id": subsection_id,
        "question": data.get("question", ""),
        "hint": data.get("hint", ""),
        "key_terms": data.get("key_terms") if isinstance(data.get("key_terms"), list) else [],
    }
    _generation_cache.set(cache_key, payload)
    _set_generation_cache_headers(response, "MISS", cache_key)
    trace_event(
        logger,
        "question.payload.completed",
        cache_status="miss",
        section_id=section_id,
        subsection_id=subsection_id,
        question_chars=len(payload["question"]),
        latency_ms=round((time.monotonic() - started) * 1000, 2),
    )
    logger.info(
        "Generation cache miss",
        extra={
            "endpoint": "test_question",
            "cache_key": cache_key[:16],
            "model": gen_model,
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
        },
    )
    return payload


# ── Evaluate Answer ────────────────────────────────────────────────────
class AnswerPayload(BaseModel):
    question: str
    answer: str
    subsection_id: str


class _ProductionAssessmentRuntime:
    """Request-scoped production adapter for Assessment Execution's internal seam."""

    def __init__(
        self,
        *,
        request: Request,
        background_tasks: BackgroundTasks,
        user: CurrentUser | None,
    ) -> None:
        self.request = request
        self.background_tasks = background_tasks
        self.user = user
        self.student_id = user.student_id if user else None
        self.authorization_present = bool(request.headers.get("authorization"))
        self.event_logger = logger

    def enforce_rate_limit(self, **values) -> None:
        enforce_rate_limit(
            self.request,
            user_key=self.student_id,
            **values,
        )

    async def load_context(self, section_id: str) -> dict:
        return await _fetch_section_meta(section_id)

    async def create_attempt(self, **values) -> None:
        if not self.student_id:
            return
        await run_in_threadpool(
            create_assessment_attempt,
            student_id=self.student_id,
            **values,
        )

    async def generate(self, **values) -> dict:
        return _generate_json_with_retry(
            values["prompt"],
            model=values["model"],
            image_data_urls=values.get("images"),
            retries=values["retries"],
            operation=values["operation"],
        )

    async def record_evaluation(self, **values) -> None:
        await run_in_threadpool(record_assessment_evaluation, **values)

    async def queue_evidence(self, **values) -> str:
        return await _queue_assessment_insights(
            background_tasks=self.background_tasks,
            request=self.request,
            user=self.user,
            **values,
        )


def _assessment_executor(
    *,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser | None,
) -> AssessmentExecutor:
    return AssessmentExecutor(
        _ProductionAssessmentRuntime(
            request=request,
            background_tasks=background_tasks,
            user=user,
        )
    )


@router.post("/sections/{section_id:path}/test/evaluate")
async def evaluate_answer(
    section_id: str,
    body: AnswerPayload,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Evaluate a written submission through the Assessment Execution module."""
    _set_no_store_headers(response)
    executor = _assessment_executor(
        request=request,
        background_tasks=background_tasks,
        user=user,
    )
    return await executor.execute(
        WrittenAnswerSubmission(
            section_id=section_id,
            subsection_id=body.subsection_id,
            question=body.question,
            answer=body.answer,
        )
    )

# ── Smart Insight Reconciliation ───────────────────────────────────────

def _reconcile_insight(
    old_insights: list[dict],
    new_type: str,
    new_content: str,
) -> dict:
    """Reconcile a new insight against all currently active matching insights."""
    if not old_insights:
        # No existing insight — use the new one as-is
        return {"type": new_type, "content": new_content}

    old_block = "\n".join(
        f'  - type: {r.get("type", "")}, content: "{(r.get("content") or "").strip()}"'
        for r in old_insights
    )

    # Ask the LLM to reconcile
    prompt = f"""Respond in STRICT JSON with exactly this schema:
{{
  "action": "REPLACE or MERGE",
  "type": "COMPETENCY or PARTIAL_UNDERSTANDING or MISCONCEPTION",
  "content": "Reconciled insight text"
}}

Do not output markdown, code fences, or additional keys.

You have multiple active learning insights about the SAME concept/source for the SAME student.

EXISTING ACTIVE INSIGHTS (most recent first):
{old_block}

NEW INSIGHT (from the current assessment):
  type: {new_type}
  content: "{new_content}"

Insight types:
- COMPETENCY: student demonstrates solid understanding
- PARTIAL_UNDERSTANDING: student understands some aspects but has gaps
- MISCONCEPTION: student holds a factually incorrect belief

Decision policy:
1. If the new insight directly contradicts the old one, use action "REPLACE".
2. If both are compatible (different, non-contradictory facets), use action "MERGE".
3. For MERGE, preserve all still-valid evidence from both insights in content.
4. For REPLACE, content should reflect the latest assessment.
5. Final type must reflect unresolved understanding level:
   - both competency -> COMPETENCY
   - any gap without clear misconception -> PARTIAL_UNDERSTANDING
   - unresolved factual error -> MISCONCEPTION
"""

    try:
        raw = _generate_reconcile_text(prompt)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        result = json.loads(raw)

        action = str(result.get("action", "")).upper()
        if action not in ("MERGE", "REPLACE"):
            action = "REPLACE"

        rtype = result.get("type", new_type)
        if rtype not in ("COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"):
            rtype = new_type

        content = result.get("content", new_content)
        if not isinstance(content, str) or not content.strip():
            content = new_content

        # Respect action explicitly. Keep the model-selected type/content when valid.
        if action == "REPLACE":
            return {"action": "REPLACE", "type": rtype, "content": content}

        return {"action": "MERGE", "type": rtype, "content": content}
    except Exception:
        # If LLM call fails, fall back to the new insight as-is
        return {"action": "REPLACE", "type": new_type, "content": new_content}


def _persist_insight(
    student_id: str,
    ins: dict,
    *,
    assessment_id: str | None = None,
    assessment_kind: str = "unknown",
    insight_index: int | None = None,
    insight_total: int | None = None,
) -> None:
    """Reconcile with any existing active insight, then persist to Neo4j.
    Modifies `ins` in-place with the reconciled type/content and sets `persisted`."""
    concept_id = ins.get("concept_id", "")
    if not concept_id:
        ins["persisted"] = False
        if assessment_id:
            assessment_event(
                logger,
                assessment_id,
                AssessmentStatus.INVARIANT_FAILED,
                assessment_kind=assessment_kind,
                stage="precondition",
                duration_ms=0.0,
                result="failure",
                reason="missing_concept_id",
                insight_index=insight_index,
                insight_total=insight_total,
            )
        raise ValueError("Cannot persist an insight without concept_id")

    db_read_started_at = time.monotonic()
    old_rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true, category: $category})
              -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
        WHERE (i)-[:ABOUT_SOURCE]->({id: $source_id})
        RETURN i.id AS id, i.type AS type, i.content AS content, i.created_at AS created_at
        ORDER BY i.created_at DESC
        """,
        _query_name="insight.lookup_active",
        student_id=student_id,
        concept_id=concept_id,
        source_id=ins["source_id"],
        category=ins["category"],
    )
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.DB_READ_COMPLETED,
            assessment_kind=assessment_kind,
            stage="db_read",
            duration_ms=elapsed_ms(db_read_started_at),
            result="success",
            insight_index=insight_index,
            insight_total=insight_total,
            prior_active_count=len(old_rows),
        )

    # Reconcile with existing insights (MERGE or REPLACE via LLM)
    reconciliation_started_at = time.monotonic()
    reconciled = _reconcile_insight(
        old_insights=old_rows,
        new_type=ins["type"],
        new_content=ins["content"],
    )
    ins["type"] = reconciled["type"]
    ins["content"] = reconciled["content"]
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.RECONCILED,
            assessment_kind=assessment_kind,
            stage="reconciliation",
            duration_ms=elapsed_ms(reconciliation_started_at),
            result="success",
            concept_id=concept_id,
            source_id=ins.get("source_id"),
            insight_index=insight_index,
            insight_total=insight_total,
            prior_active_count=len(old_rows),
            reconcile_action=reconciled.get("action", "NEW"),
            reconciled_type=ins["type"],
        )
    embedding_started_at = time.monotonic()
    ins["embedding"] = _embed_text_with_fireworks(ins["content"], retries=2)
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.EMBEDDED,
            assessment_kind=assessment_kind,
            stage="embedding",
            duration_ms=elapsed_ms(embedding_started_at),
            result="success",
            model=settings.FIREWORKS_EMBEDDING_MODEL,
            concept_id=concept_id,
            insight_index=insight_index,
            insight_total=insight_total,
            embedding_dimensions=len(ins["embedding"]),
            embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
        )

    insight_id = f"insight:{uuid.uuid4().hex}"
    db_write_started_at = time.monotonic()
    try:
        rows = write_query(
            """
        MATCH (s:Student {id: $student_id})
        MATCH (source {id: $source_id})
        MATCH (concept:Concept {id: $concept_id})
        OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(old:Insight {is_active: true, category: $category})
                      -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
        WHERE (old)-[:ABOUT_SOURCE]->({id: $source_id})
        SET old.is_active = false
        WITH s, source, concept, collect(old) AS old_insights
        OPTIONAL MATCH (attempt:AssessmentAttempt {id: $assessment_id})
        WITH s, source, concept, old_insights, attempt

        CREATE (new:Insight {
            id:         $insight_id,
            assessment_id: $assessment_id,
            type:       $type,
            category:   $category,
            content:    $content,
            embedding:  $embedding,
            embedding_model: $embedding_model,
            is_active:  true,
            created_at: datetime()
        })
        CREATE (s)-[:HAS_INSIGHT]->(new)

        WITH s, new, old_insights, source, concept, attempt
        CREATE (new)-[:ABOUT_SOURCE]->(source)
        CREATE (new)-[:ABOUT_CONCEPT]->(concept)
        FOREACH (_ IN CASE WHEN attempt IS NULL THEN [] ELSE [1] END |
            MERGE (attempt)-[:PRODUCED]->(new))

        FOREACH (old IN old_insights | CREATE (new)-[:SUPERSEDES]->(old))
        // Concurrency safety: enforce only one active insight for this key.
        WITH s, new
        OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(other:Insight {is_active: true, category: $category})
                       -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
        WHERE other.id <> new.id AND (other)-[:ABOUT_SOURCE]->({id: $source_id})
        WITH new, [candidate IN collect(other) WHERE candidate IS NOT NULL] AS competing_insights
        FOREACH (other IN competing_insights | SET other.is_active = false)
        RETURN new.id AS id
            """,
            _query_name="insight.persist",
            student_id=student_id,
            insight_id=insight_id,
            assessment_id=assessment_id,
            type=ins["type"],
            category=ins["category"],
            content=ins["content"],
            embedding=ins["embedding"],
            embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
            source_id=ins["source_id"],
            concept_id=concept_id,
        )
    except Exception as exc:
        if assessment_id:
            assessment_event(
                logger,
                assessment_id,
                AssessmentStatus.INVARIANT_FAILED,
                assessment_kind=assessment_kind,
                stage="db_write",
                duration_ms=elapsed_ms(db_write_started_at),
                result="failure",
                reason="database_write_failed",
                error_type=type(exc).__name__,
                concept_id=concept_id,
                insight_index=insight_index,
                insight_total=insight_total,
            )
        raise
    ins["persisted"] = bool(rows)
    if not rows:
        if assessment_id:
            assessment_event(
                logger,
                assessment_id,
                AssessmentStatus.INVARIANT_FAILED,
                assessment_kind=assessment_kind,
                stage="db_write",
                duration_ms=elapsed_ms(db_write_started_at),
                result="failure",
                reason="insight_create_returned_no_rows",
                concept_id=concept_id,
                insight_index=insight_index,
                insight_total=insight_total,
            )
        raise RuntimeError("Insight write completed without creating a record")
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.PERSISTED,
            assessment_kind=assessment_kind,
            stage="db_write",
            duration_ms=elapsed_ms(db_write_started_at),
            result="success",
            concept_id=concept_id,
            source_id=ins.get("source_id"),
            insight_id=rows[0].get("id"),
            insight_index=insight_index,
            insight_total=insight_total,
        )


def _record_persistence_failure(
    student_id: str,
    ins: dict,
    error: str,
    *,
    assessment_id: str | None = None,
    assessment_kind: str = "unknown",
    insight_index: int | None = None,
    insight_total: int | None = None,
) -> None:
    """Best-effort dead-letter record for failed background persistence."""
    dead_letter_started_at = time.monotonic()
    try:
        write_query(
            """
            CREATE (f:InsightPersistenceFailure {
                id: $failure_id,
                assessment_id: $assessment_id,
                student_id: $student_id,
                concept_id: $concept_id,
                source_id: $source_id,
                category: $category,
                insight_type: $insight_type,
                content: $content,
                error: $error,
                created_at: datetime()
            })
            """,
            _query_name="insight.dead_letter",
            failure_id=f"insight_failure:{uuid.uuid4().hex}",
            assessment_id=assessment_id,
            student_id=student_id,
            concept_id=ins.get("concept_id"),
            source_id=ins.get("source_id"),
            category=ins.get("category"),
            insight_type=ins.get("type"),
            content=ins.get("content"),
            error=error[:2000],
        )
        if assessment_id:
            assessment_event(
                logger,
                assessment_id,
                AssessmentStatus.DEAD_LETTER_RECORDED,
                assessment_kind=assessment_kind,
                stage="dead_letter",
                duration_ms=elapsed_ms(dead_letter_started_at),
                result="success",
                insight_index=insight_index,
                insight_total=insight_total,
            )
    except Exception as exc:
        if assessment_id:
            assessment_event(
                logger,
                assessment_id,
                AssessmentStatus.INVARIANT_FAILED,
                assessment_kind=assessment_kind,
                stage="dead_letter",
                duration_ms=elapsed_ms(dead_letter_started_at),
                result="failure",
                reason="dead_letter_write_failed",
                error_type=type(exc).__name__,
                insight_index=insight_index,
                insight_total=insight_total,
            )
        logger.exception(
            "Failed to write insight persistence dead-letter record",
            extra={"student_id": student_id, "concept_id": ins.get("concept_id")},
        )


def _persist_insight_safe(
    student_id: str,
    ins: dict,
    *,
    assessment_id: str | None = None,
    assessment_kind: str = "unknown",
    assessment_started_at: float | None = None,
    queued_at: float | None = None,
    insight_index: int | None = None,
    insight_total: int | None = None,
) -> None:
    """Background wrapper: never let persistence errors fail the response path."""
    persistence_started_at = time.monotonic()
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.PERSISTENCE_STARTED,
            assessment_kind=assessment_kind,
            stage="queue_wait",
            duration_ms=elapsed_ms(queued_at) if queued_at is not None else 0.0,
            result="success",
            insight_index=insight_index,
            insight_total=insight_total,
        )
    last_error = ""
    for attempt in range(2):
        attempt_started_at = time.monotonic()
        try:
            _persist_insight(
                student_id,
                ins,
                assessment_id=assessment_id,
                assessment_kind=assessment_kind,
                insight_index=insight_index,
                insight_total=insight_total,
            )
            invalidate_student_insight_cache(student_id)
            if assessment_id:
                record_assessment_insight_result(
                    assessment_id=assessment_id,
                    success=True,
                )
            if assessment_id:
                assessment_event(
                    logger,
                    assessment_id,
                    AssessmentStatus.PERSISTENCE_ATTEMPT_COMPLETED,
                    assessment_kind=assessment_kind,
                    stage="persistence_attempt",
                    duration_ms=elapsed_ms(attempt_started_at),
                    result="success",
                    attempt=attempt + 1,
                    attempt_limit=2,
                    insight_index=insight_index,
                    insight_total=insight_total,
                )
                assessment_event(
                    logger,
                    assessment_id,
                    AssessmentStatus.PERSISTENCE_COMPLETED,
                    assessment_kind=assessment_kind,
                    stage="persistence_total",
                    duration_ms=elapsed_ms(persistence_started_at),
                    result="success",
                    insight_index=insight_index,
                    insight_total=insight_total,
                )
                if assessment_started_at is not None and insight_index == insight_total:
                    assessment_event(
                        logger,
                        assessment_id,
                        AssessmentStatus.ASSESSMENT_COMPLETED,
                        assessment_kind=assessment_kind,
                        stage="assessment_total",
                        duration_ms=elapsed_ms(assessment_started_at),
                        result="success",
                        insight_total=insight_total,
                    )
            return
        except Exception as exc:
            last_error = str(exc)
            has_another_attempt = attempt + 1 < 2
            if assessment_id and has_another_attempt:
                assessment_event(
                    logger,
                    assessment_id,
                    AssessmentStatus.PERSISTENCE_RETRY,
                    assessment_kind=assessment_kind,
                    stage="persistence_attempt",
                    duration_ms=elapsed_ms(attempt_started_at),
                    result="retry",
                    failed_attempt=attempt + 1,
                    next_attempt=attempt + 2,
                    attempt_limit=2,
                    concept_id=ins.get("concept_id"),
                    source_id=ins.get("source_id"),
                    insight_index=insight_index,
                    insight_total=insight_total,
                    error_type=type(exc).__name__,
                )
            logger.exception(
                "Insight persistence failed (attempt %s/2)",
                attempt + 1,
                extra={
                    "student_id": student_id,
                    "concept_id": ins.get("concept_id"),
                    "source_id": ins.get("source_id"),
                    "category": ins.get("category"),
                    "error": last_error,
                },
            )
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.PERSISTENCE_FAILED,
            assessment_kind=assessment_kind,
            stage="persistence_attempt",
            duration_ms=elapsed_ms(attempt_started_at),
            result="failure",
            concept_id=ins.get("concept_id"),
            source_id=ins.get("source_id"),
            insight_index=insight_index,
            insight_total=insight_total,
        )
    _record_persistence_failure(
        student_id,
        ins,
        last_error or "unknown error",
        assessment_id=assessment_id,
        assessment_kind=assessment_kind,
        insight_index=insight_index,
        insight_total=insight_total,
    )
    if assessment_id:
        record_assessment_insight_result(
            assessment_id=assessment_id,
            success=False,
            error=last_error or "unknown error",
        )
    if assessment_id:
        assessment_event(
            logger,
            assessment_id,
            AssessmentStatus.PERSISTENCE_COMPLETED,
            assessment_kind=assessment_kind,
            stage="persistence_total",
            duration_ms=elapsed_ms(persistence_started_at),
            result="failure",
            insight_index=insight_index,
            insight_total=insight_total,
        )
        if assessment_started_at is not None and insight_index == insight_total:
            assessment_event(
                logger,
                assessment_id,
                AssessmentStatus.ASSESSMENT_COMPLETED,
                assessment_kind=assessment_kind,
                stage="assessment_total",
                duration_ms=elapsed_ms(assessment_started_at),
                result="failure",
                insight_total=insight_total,
            )


# ── MCQ Generation ─────────────────────────────────────────────────────

@router.get("/sections/{section_id:path}/test/mcq")
async def generate_mcq(
    section_id: str,
    subsection_id: str,
    request: Request,
    response: Response,
    variant: int = 0,
):
    """Generate an MCQ from one subsection, with its section as reference context."""
    trace_event(
        logger,
        "mcq.request.started",
        section_id=section_id,
        subsection_id=subsection_id,
        variant=variant,
    )
    metadata_started = time.monotonic()
    try:
        meta = await _fetch_section_meta(section_id)
    except Exception as exc:
        trace_exception(
            logger,
            "mcq.metadata_fetch.failed",
            exc,
            section_id=section_id,
            latency_ms=round((time.monotonic() - metadata_started) * 1000, 2),
        )
        raise
    trace_event(
        logger,
        "mcq.metadata_fetch.completed",
        section_id=section_id,
        latency_ms=round((time.monotonic() - metadata_started) * 1000, 2),
        subsection_count=len(meta["subsections"]),
        concept_count=len(meta["concepts"]),
        context_chars=len(meta["full_text"]),
    )
    context = meta["full_text"]

    target_sub = _resolve_target_subsection(meta, subsection_id, section_id)
    enforce_rate_limit(request, scope="test_mcq_generation", limit=30, window_seconds=60)

    generation_targets = default_generation_targets()
    provider = generation_targets[0].provider
    gen_model = generation_targets[0].model

    cache_key = stable_cache_key(
        "test_mcq:v2",
        {
            "section_id": section_id,
            "subsection_id": target_sub["id"],
            "variant": variant,
            "provider": provider,
            "model": gen_model,
            "fallbacks": [f"{target.provider}:{target.model}" for target in generation_targets[1:]],
            "prompt_version": settings.GEN_PROMPT_VERSION,
        },
    )
    cache_started = time.monotonic()
    cached = _generation_cache.get(cache_key)
    trace_event(
        logger,
        "mcq.cache_lookup.completed",
        cache_key_fingerprint=cache_key[:16],
        status="hit" if cached is not None else "miss",
        latency_ms=round((time.monotonic() - cache_started) * 1000, 2),
    )
    if cached is not None:
        if not _valid_mcq_payload(cached):
            _generation_cache.delete(cache_key)
        else:
            _set_generation_cache_headers(response, "HIT", cache_key)
            logger.info(
                "Generation cache hit",
                extra={"endpoint": "test_mcq", "cache_key": cache_key[:16], "model": gen_model},
            )
            trace_event(
                logger,
                "mcq.request.completed",
                cache_status="hit",
                section_id=section_id,
                subsection_id=target_sub["id"],
            )
            return cached

    started = time.monotonic()
    prompt = f"""You are an educational assessment AI. Based on the following study material,
generate ONE conceptual multiple-choice question (MCQ) that tests deep understanding
(not simple recall). The question should require the student to apply, analyze, or
connect ideas that appear in the target subsection.

The student is currently studying this subsection:
- subsection_id: "{target_sub["id"]}"
- title: "{target_sub["title"]}"

Generate the MCQ for THIS SUBSECTION ONLY.
Do NOT generate a question about any other subsection.

TARGET SUBSECTION CONTENT (primary assessment scope):
{target_sub["content"]}

FULL SECTION REFERENCE CONTEXT (definitions and surrounding context only):
{context}

Respond in STRICT JSON with exactly these keys:
{{
  "question": "The question text (clear, conceptual, thought-provoking)",
  "options": {{
    "A": "First option text",
    "B": "Second option text",
    "C": "Third option text",
    "D": "Fourth option text"
  }},
  "correct_answer": "A or B or C or D",
  "explanation": "2-3 sentences explaining WHY the correct answer is right and others are wrong",
  "subsection_id": "{target_sub["id"]}",
  "key_terms": ["term1", "term2", "term3"]
}}

The four choices MUST be inside the "options" object. Do not return A, B, C,
or D as top-level JSON keys.

RULES:
- Make all 4 options plausible (no obviously silly answers)
- The question should test understanding, NOT memorization
- Distractors should reflect common misconceptions
- The question must be answerable from the target subsection content.
- Use the full section only to clarify notation, definitions, or context needed to
  understand the target subsection.
- Do not test a sibling subsection or any linked concept that is absent from the
  target subsection.
- Return ONLY valid JSON, no markdown fences, no extra text."""

    trace_event(
        logger,
        "mcq.provider.selected",
        provider=provider,
        model=gen_model,
        cache_key_fingerprint=cache_key[:16],
    )
    try:
        data = _generate_json_with_retry(
            prompt,
            model=gen_model,
            retries=2,
            operation="mcq_generation",
            max_tokens=MCQ_MAX_TOKENS,
            json_schema=SECTION_MCQ_JSON_SCHEMA,
            schema_name="section_mcq",
        )
    except Exception as exc:
        trace_exception(
            logger,
            "mcq.generation.failed",
            exc,
            provider=provider,
            model=gen_model,
            section_id=section_id,
            subsection_id=target_sub["id"],
            cache_key_fingerprint=cache_key[:16],
            latency_ms=round((time.monotonic() - started) * 1000, 2),
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to generate MCQ. The AI returned an invalid response. Please try again.",
        ) from exc

    data = normalize_mcq_options(data)

    # Validate subsection_id — force to requested subsection for safety.
    if data.get("subsection_id") != target_sub["id"]:
        data["subsection_id"] = target_sub["id"]

    payload = {
        "section_id": section_id,
        "section_title": meta["section_title"],
        "subsection_id": target_sub["id"],
        "question": data.get("question", ""),
        "options": data.get("options", {}),
        "correct_answer": data.get("correct_answer", "A"),
        "explanation": data.get("explanation", ""),
        "key_terms": data.get("key_terms") if isinstance(data.get("key_terms"), list) else [],
    }
    validation_errors = mcq_validation_errors(
        payload,
        require_subsection=True,
        require_key_terms=True,
    )
    if validation_errors:
        trace_event(
            logger,
            "mcq.payload.invalid",
            section_id=section_id,
            subsection_id=target_sub["id"],
            model=gen_model,
            option_count=len(payload["options"]) if isinstance(payload["options"], dict) else 0,
            validation_errors=validation_errors,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to generate a complete MCQ. Please try again.",
        )
    _generation_cache.set(cache_key, payload)
    _set_generation_cache_headers(response, "MISS", cache_key)
    trace_event(
        logger,
        "mcq.payload.completed",
        cache_status="miss",
        section_id=section_id,
        subsection_id=target_sub["id"],
        question_chars=len(payload["question"]),
        option_count=len(payload["options"]),
        latency_ms=round((time.monotonic() - started) * 1000, 2),
    )
    logger.info(
        "Generation cache miss",
        extra={
            "endpoint": "test_mcq",
            "cache_key": cache_key[:16],
            "model": gen_model,
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
        },
    )
    return payload


# ── MCQ Evaluation ─────────────────────────────────────────────────────
class MCQAnswerPayload(BaseModel):
    question: str
    options: dict
    selected: str          # "A", "B", "C", or "D"
    correct_answer: str    # "A", "B", "C", or "D"
    subsection_id: str


@router.post("/sections/{section_id:path}/test/mcq/evaluate")
async def evaluate_mcq(
    section_id: str,
    body: MCQAnswerPayload,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Evaluate an MCQ submission through the Assessment Execution module."""
    _set_no_store_headers(response)
    executor = _assessment_executor(
        request=request,
        background_tasks=background_tasks,
        user=user,
    )
    return await executor.execute(
        MCQSubmission(
            section_id=section_id,
            subsection_id=body.subsection_id,
            question=body.question,
            options=body.options,
            selected=body.selected,
            correct_answer=body.correct_answer,
        )
    )


class ExerciseAnswerPayload(BaseModel):
    exercise_id: str
    problem: str
    answer_mode: Literal["text", "image"]
    answer_text: str | None = None
    answer_images: list[str] | None = None


@router.post("/sections/{section_id:path}/test/exercises/evaluate")
async def evaluate_exercise_answer(
    section_id: str,
    body: ExerciseAnswerPayload,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Evaluate an exercise submission through the Assessment Execution module."""
    _set_no_store_headers(response)
    executor = _assessment_executor(
        request=request,
        background_tasks=background_tasks,
        user=user,
    )
    return await executor.execute(
        ExerciseSubmission(
            section_id=section_id,
            exercise_id=body.exercise_id,
            problem=body.problem,
            answer_mode=body.answer_mode,
            answer_text=body.answer_text,
            answer_images=body.answer_images,
        )
    )
