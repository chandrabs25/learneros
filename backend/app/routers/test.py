"""
LearnerOS — Test Me Router
─────────────────────────
Generates comprehension questions from section content using Fireworks-hosted Kimi 2.5,
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
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Response
from app.auth import get_optional_user, CurrentUser
from openai import OpenAI

from app.config import settings
from app.database import read_query, write_query
from app.services.generation_cache import build_generation_cache, stable_cache_key

router = APIRouter(prefix="/api", tags=["test"])
logger = logging.getLogger(__name__)

# ── Fireworks OpenAI-compatible client (lazy singleton) ─────────────────
_client: OpenAI | None = None
_embedding_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.FIREWORKS_API_KEY:
            raise HTTPException(status_code=500, detail="FIREWORKS_API_KEY not configured")
        _client = OpenAI(
            api_key=settings.FIREWORKS_API_KEY,
            base_url=settings.FIREWORKS_BASE_URL,
        )
    return _client


def _get_embedding_client() -> OpenAI:
    global _embedding_client
    if _embedding_client is None:
        api_key = settings.FIREWORKS_API_KEY_EMBEDDINGS or settings.FIREWORKS_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="FIREWORKS_API_KEY_EMBEDDINGS (or FIREWORKS_API_KEY) not configured",
            )
        _embedding_client = OpenAI(
            api_key=api_key,
            base_url=settings.FIREWORKS_BASE_URL,
        )
    return _embedding_client


MODEL = settings.FIREWORKS_MODEL
EVAL_MODEL = settings.FIREWORKS_MODEL
EXERCISE_EVAL_MODEL = "gemini-3.1-pro-preview"
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
    """Generate reconciliation output text via Fireworks Kimi."""
    return _generate_with_fireworks(prompt, model=EVAL_MODEL, temperature=0.1, json_mode=True)


def _generate_with_fireworks(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    client = _get_client()
    kwargs = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Return only valid JSON matching the requested schema."
                if json_mode
                else "You are a helpful educational assistant.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "timeout": 60,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return str(content or "").strip()


def _generate_json_with_retry(prompt: str, *, model: str, retries: int = 2) -> dict:
    data = None
    for attempt in range(retries):
        raw = _generate_with_fireworks(prompt, model=model, temperature=0.0, json_mode=True)
        try:
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0]
            data = json.loads(raw)
            break
        except (json.JSONDecodeError, IndexError):
            if attempt == retries - 1:
                raise
    return data


def _embed_text_with_fireworks(text: str, retries: int = 2) -> list[float]:
    """Create an embedding vector for text using Fireworks embeddings API."""
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Cannot embed empty insight content")

    last_err: Exception | None = None
    for _ in range(retries):
        try:
            client = _get_embedding_client()
            resp = client.embeddings.create(
                model=settings.FIREWORKS_EMBEDDING_MODEL,
                input=clean_text,
            )
            vector = resp.data[0].embedding if resp.data else None
            if not vector:
                raise ValueError("Embedding API returned empty vector")
            return [float(x) for x in vector]
        except Exception as exc:  # pragma: no cover
            last_err = exc
    raise RuntimeError(f"Embedding generation failed: {last_err}")


def _parse_data_url_image(image_data_url: str) -> tuple[str, str]:
    """Parse a data URL image into (mime_type, base64_data)."""
    if not image_data_url.startswith("data:"):
        raise ValueError("image must be a data URL")
    header, b64_data = image_data_url.split(",", 1)
    if ";base64" not in header:
        raise ValueError("image data URL must be base64 encoded")
    mime_type = header[5:].split(";")[0] or "image/jpeg"
    if not b64_data.strip():
        raise ValueError("image base64 payload is empty")
    return mime_type, b64_data


def _generate_gemini_json_with_retry(
    prompt: str,
    *,
    model: str,
    image_data_urls: list[str] | None = None,
    retries: int = 2,
) -> dict:
    """Generate strict JSON via Gemini REST API; supports optional image inputs."""
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    parts: list[dict] = [{"text": prompt}]
    for data_url in image_data_urls or []:
        mime_type, b64_data = _parse_data_url_image(data_url)
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_data,
                }
            }
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urlparse.quote(model, safe='')}:generateContent?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }
    body = json.dumps(payload).encode("utf-8")

    for attempt in range(retries):
        try:
            req = urlrequest.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            parts = (
                parsed.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, KeyError, IndexError, urlerror.URLError, ValueError):
            if attempt == retries - 1:
                raise

    raise RuntimeError("Gemini call failed after retries")


# ── Helpers ────────────────────────────────────────────────────────────

def _fetch_section_meta(section_id: str) -> dict:
    """Return all relevant section data for prompts and insight creation."""
    # Subsection text
    rows = read_query(
        """
        MATCH (sec:Section {id: $section_id})-[:CONTAINS]->(ss:Subsection)
        RETURN sec.title       AS section_title,
               ss.id           AS sub_id,
               ss.title        AS sub_title,
               ss.content_text AS content
        ORDER BY ss.order
        """,
        section_id=section_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No content found for {section_id}")

    section_title = rows[0].get("section_title") or section_id
    subsections = [
        {"id": r["sub_id"], "title": r.get("sub_title") or r["sub_id"]}
        for r in rows if r.get("sub_id")
    ]
    text_blocks: list[str] = []
    for r in rows:
        title = r.get("sub_title") or ""
        sub_id = r.get("sub_id") or ""
        body = r.get("content") or ""
        
        header = f"### {title}" if title else "###"
        if sub_id:
            header += f" (subsection_id: {sub_id})"
        
        text_blocks.append(f"{header}\n{body}")
        
    full_text = "\n\n".join(text_blocks)

    # Concepts for evaluation context:
    # Always include all prerequisite concepts used by subsections in the same chapter.
    # Also include section-level prerequisite concepts in that chapter as a fallback.
    concept_rows = read_query(
        """
        MATCH (sec:Section {id: $section_id})<-[:CONTAINS]-(ch:Chapter)-[:CONTAINS]->(sec2:Section)
        OPTIONAL MATCH (sec2)-[:CONTAINS]->(ss:Subsection)-[:REQUIRES]->(c_sub:Concept)
        OPTIONAL MATCH (sec2)-[:REQUIRES]->(c_sec:Concept)
        WITH collect(DISTINCT c_sub) + collect(DISTINCT c_sec) AS all_concepts
        UNWIND all_concepts AS c
        WITH DISTINCT c
        WHERE c IS NOT NULL
        RETURN DISTINCT c.id AS id, c.name AS name
        """,
        section_id=section_id,
    )
    # Deduplicate by concept id (UNION DISTINCT handles Cypher-level, but belt-and-suspenders)
    seen_ids = set()
    concepts = []
    for r in concept_rows:
        cid = r.get("id")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            concepts.append({"id": cid, "name": (r["name"] or "").replace("_", " ").title()})
    key_terms = [c["name"] for c in concepts]

    return {
        "section_id": section_id,
        "section_title": section_title,
        "subsections": subsections,
        "full_text": full_text,
        "concepts": concepts,
        "key_terms": key_terms,
    }


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


def _valid_question_payload(data: dict) -> bool:
    return (
        isinstance(data.get("question"), str)
        and isinstance(data.get("subsection_id"), str)
        and isinstance(data.get("hint"), str)
        and isinstance(data.get("key_terms"), list)
    )


def _valid_mcq_payload(data: dict) -> bool:
    options = data.get("options")
    return (
        isinstance(data.get("question"), str)
        and isinstance(options, dict)
        and all(k in options for k in ("A", "B", "C", "D"))
        and data.get("correct_answer") in ("A", "B", "C", "D")
        and isinstance(data.get("explanation"), str)
        and isinstance(data.get("subsection_id"), str)
        and isinstance(data.get("key_terms"), list)
    )


# ── Generate Question ──────────────────────────────────────────────────
@router.get("/sections/{section_id:path}/test/question")
async def generate_question(
    section_id: str,
    subsection_id: str,
    response: Response,
    variant: int = 0,
):
    """Generate an AI question from section content, targeting the given subsection.
    The subsection_id is required — the question is always about one specific subsection.
    If authenticated, incorporates the student's known misconceptions
    on prerequisite concepts to target weak areas."""
    meta = _fetch_section_meta(section_id)
    context = meta["full_text"]

    # Resolve target subsection
    valid_sub_ids = {s["id"] for s in meta["subsections"]}
    if subsection_id not in valid_sub_ids:
        raise HTTPException(
            status_code=400,
            detail=f"subsection_id '{subsection_id}' not found in section '{section_id}'",
        )
    target_sub = next(s for s in meta["subsections"] if s["id"] == subsection_id)

    cache_key = stable_cache_key(
        "test_question",
        {
            "section_id": section_id,
            "subsection_id": target_sub["id"],
            "variant": variant,
            "model": MODEL,
            "prompt_version": settings.GEN_PROMPT_VERSION,
        },
    )
    cached = _generation_cache.get(cache_key)
    if cached is not None:
        if not _valid_question_payload(cached):
            _generation_cache.delete(cache_key)
        else:
            _set_generation_cache_headers(response, "HIT", cache_key)
            logger.info(
                "Generation cache hit",
                extra={"endpoint": "test_question", "cache_key": cache_key[:16], "model": MODEL},
            )
            return cached

    started = time.monotonic()
    prompt = f"""You are an educational assessment AI.

The student is currently studying the subsection "{target_sub["title"]}" 
(subsection_id: "{target_sub["id"]}").

Generate ONE thought-provoking comprehension question that tests deep understanding 
(not simple recall) about THIS SPECIFIC SUBSECTION ONLY. The question should require 
the student to explain, analyze, or connect concepts from this subsection.

Do NOT generate a question about any other subsection or topic outside this subsection.

FULL STUDY MATERIAL (for reference context):
{context}

Respond in STRICT JSON with exactly these keys:
{{
  "question": "The question text",
  "subsection_id": "{target_sub["id"]}",
  "hint": "A brief hint or pro-tip to help the student think about the answer (1-2 sentences)",
  "key_terms": ["term1", "term2", "term3"]
}}

The key_terms should be 3-6 important concepts from this subsection that the student should mention.
Return ONLY valid JSON, no markdown fences, no extra text."""

    try:
        data = _generate_json_with_retry(prompt, model=MODEL, retries=2)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate question. The AI returned an invalid response. Please try again.",
        )

    # Validate subsection_id — fall back to first subsection if invalid
    valid_sub_ids = {s["id"] for s in meta["subsections"]}
    subsection_id = data.get("subsection_id", "")
    if subsection_id not in valid_sub_ids:
        subsection_id = meta["subsections"][0]["id"] if meta["subsections"] else section_id

    payload = {
        "section_id": section_id,
        "section_title": meta["section_title"],
        "subsection_id": subsection_id,
        "question": data.get("question", ""),
        "hint": data.get("hint", ""),
        "key_terms": data.get("key_terms", meta["key_terms"][:5]),
    }
    _generation_cache.set(cache_key, payload)
    _set_generation_cache_headers(response, "MISS", cache_key)
    logger.info(
        "Generation cache miss",
        extra={
            "endpoint": "test_question",
            "cache_key": cache_key[:16],
            "model": MODEL,
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
        },
    )
    return payload


# ── Evaluate Answer ────────────────────────────────────────────────────
class AnswerPayload(BaseModel):
    question: str
    answer: str
    subsection_id: str


@router.post("/sections/{section_id:path}/test/evaluate")
async def evaluate_answer(
    section_id: str,
    body: AnswerPayload,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Evaluate a student's answer and return structured insights.
    If authenticated, auto-persists insights to Neo4j."""
    _set_no_store_headers(response)
    meta = _fetch_section_meta(section_id)
    context = meta["full_text"]

    # The subsection_id comes from the question generation step — no guessing
    source_id = body.subsection_id

    # Build concept list for the LLM
    concept_list = "\n".join(
        f'  - concept_id: "{c["id"]}", name: "{c["name"]}"'
        for c in meta["concepts"]
    ) or "  (no concepts linked)"

    prompt = f"""You are an expert teacher evaluating a student's answer.

STUDY MATERIAL (ground truth):
{context}

QUESTION: {body.question}

STUDENT'S ANSWER: {body.answer}

CONCEPTS LINKED TO THIS SECTION:
{concept_list}

─── TASK ───

1. Evaluate the student's answer for accuracy, completeness, and depth.
2. Generate learning insights ONLY for concepts that the QUESTION DIRECTLY 
   tests and the ANSWER meaningfully addresses (correctly or incorrectly).
   
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

    try:
        data = _generate_json_with_retry(prompt, model=EVAL_MODEL, retries=1)
    except Exception:
        data = {
            "score": 50,
            "grade": "C",
            "feedback": "Could not fully evaluate. Please try again.",
            "strengths": [],
            "improvements": ["Try providing more detail"],
            "model_answer": "",
            "insights": [],
        }

    # Validate insight entries
    valid_concept_ids = {c["id"] for c in meta["concepts"]}

    insights = []
    for ins in data.get("insights", []):
        concept_id = ins.get("concept_id", "")
        ins_type = ins.get("type", "")
        ins_category = ins.get("category", "conceptual")

        # Skip if concept is not actually linked to this section
        if concept_id not in valid_concept_ids:
            continue
        # Skip if type is invalid
        if ins_type not in ("COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"):
            continue
        # Skip if category is invalid
        if ins_category not in ("conceptual", "mathematical"):
            continue

        insights.append({
            "concept_id": concept_id,
            "concept_name": ins.get("concept_name", ""),
            "type": ins_type,
            "category": ins_category,
            "content": ins.get("content", ""),
            "source_id": source_id,  # deterministic, from question generation
        })

    # Auto-persist insights in the background so evaluation response is not blocked.
    auth_header_present = bool(request.headers.get("authorization"))
    persistence_status = "skipped_no_insights"
    if user and insights:
        persistence_status = "queued"
        for ins in insights:
            background_tasks.add_task(_persist_insight_safe, user.student_id, dict(ins))
    elif not user:
        persistence_status = (
            "skipped_invalid_auth" if auth_header_present else "skipped_unauthenticated"
        )

    data["insights"] = insights
    data["section_id"] = section_id
    data["persistence_status"] = persistence_status

    return data


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


def _persist_insight(student_id: str, ins: dict) -> None:
    """Reconcile with any existing active insight, then persist to Neo4j.
    Modifies `ins` in-place with the reconciled type/content and sets `persisted`."""
    concept_id = ins.get("concept_id", "")
    if not concept_id:
        ins["persisted"] = False
        return

    old_rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true, category: $category})
              -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
        WHERE (i)-[:ABOUT_SOURCE]->({id: $source_id})
        RETURN i.id AS id, i.type AS type, i.content AS content, i.created_at AS created_at
        ORDER BY i.created_at DESC
        """,
        student_id=student_id,
        concept_id=concept_id,
        source_id=ins["source_id"],
        category=ins["category"],
    )

    # Reconcile with existing insights (MERGE or REPLACE via LLM)
    reconciled = _reconcile_insight(
        old_insights=old_rows,
        new_type=ins["type"],
        new_content=ins["content"],
    )
    ins["type"] = reconciled["type"]
    ins["content"] = reconciled["content"]
    ins["embedding"] = _embed_text_with_fireworks(ins["content"], retries=2)

    insight_id = f"insight:{uuid.uuid4().hex}"
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

        CREATE (new:Insight {
            id:         $insight_id,
            type:       $type,
            category:   $category,
            content:    $content,
            embedding:  $embedding,
            embedding_model: $embedding_model,
            is_active:  true,
            created_at: datetime()
        })
        CREATE (s)-[:HAS_INSIGHT]->(new)

        WITH s, new, old_insights, source, concept
        CREATE (new)-[:ABOUT_SOURCE]->(source)
        CREATE (new)-[:ABOUT_CONCEPT]->(concept)

        FOREACH (old IN old_insights | CREATE (new)-[:SUPERSEDES]->(old))
        // Concurrency safety: enforce only one active insight for this key.
        WITH s, new
        MATCH (s)-[:HAS_INSIGHT]->(other:Insight {is_active: true, category: $category})
              -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
        WHERE other.id <> new.id AND (other)-[:ABOUT_SOURCE]->({id: $source_id})
        SET other.is_active = false
        RETURN new.id AS id
        """,
        student_id=student_id,
        insight_id=insight_id,
        type=ins["type"],
        category=ins["category"],
        content=ins["content"],
        embedding=ins["embedding"],
        embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
        source_id=ins["source_id"],
        concept_id=concept_id,
    )
    ins["persisted"] = bool(rows)


def _record_persistence_failure(student_id: str, ins: dict, error: str) -> None:
    """Best-effort dead-letter record for failed background persistence."""
    try:
        write_query(
            """
            CREATE (f:InsightPersistenceFailure {
                id: $failure_id,
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
            failure_id=f"insight_failure:{uuid.uuid4().hex}",
            student_id=student_id,
            concept_id=ins.get("concept_id"),
            source_id=ins.get("source_id"),
            category=ins.get("category"),
            insight_type=ins.get("type"),
            content=ins.get("content"),
            error=error[:2000],
        )
    except Exception:
        logger.exception(
            "Failed to write insight persistence dead-letter record",
            extra={"student_id": student_id, "concept_id": ins.get("concept_id")},
        )


def _persist_insight_safe(student_id: str, ins: dict) -> None:
    """Background wrapper: never let persistence errors fail the response path."""
    last_error = ""
    for attempt in range(2):
        try:
            _persist_insight(student_id, ins)
            return
        except Exception as exc:
            last_error = str(exc)
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
    _record_persistence_failure(student_id, ins, last_error or "unknown error")


# ── MCQ Generation ─────────────────────────────────────────────────────

@router.get("/sections/{section_id:path}/test/mcq")
async def generate_mcq(
    section_id: str,
    subsection_id: str,
    response: Response,
    concept_id: str | None = None,
    variant: int = 0,
):
    """Generate a conceptual MCQ from full section context, targeted to one subsection."""
    meta = _fetch_section_meta(section_id)
    context = meta["full_text"]

    # Resolve target subsection
    valid_sub_ids = {s["id"] for s in meta["subsections"]}
    if subsection_id not in valid_sub_ids:
        raise HTTPException(
            status_code=400,
            detail=f"subsection_id '{subsection_id}' not found in section '{section_id}'",
        )
    target_sub = next(s for s in meta["subsections"] if s["id"] == subsection_id)

    focus_concept = None
    if concept_id:
        concept_map = {c["id"]: c for c in meta["concepts"]}
        if concept_id not in concept_map:
            raise HTTPException(
                status_code=400,
                detail=f"concept_id '{concept_id}' not linked to section '{section_id}'",
            )
        focus_concept = concept_map[concept_id]

    concept_focus_block = ""
    concept_rule = ""
    if focus_concept:
        concept_focus_block = (
            "\nFOCUS CONCEPT:\n"
            f'- concept_id: "{focus_concept["id"]}"\n'
            f'- concept_name: "{focus_concept["name"]}"\n'
        )
        concept_rule = (
            "\n- The question MUST directly test the FOCUS CONCEPT.\n"
            "- Make distractors around common confusion related to this concept."
        )

    cache_key = stable_cache_key(
        "test_mcq",
        {
            "section_id": section_id,
            "subsection_id": target_sub["id"],
            "concept_id": concept_id or "",
            "variant": variant,
            "model": MODEL,
            "prompt_version": settings.GEN_PROMPT_VERSION,
        },
    )
    cached = _generation_cache.get(cache_key)
    if cached is not None:
        if not _valid_mcq_payload(cached):
            _generation_cache.delete(cache_key)
        else:
            _set_generation_cache_headers(response, "HIT", cache_key)
            logger.info(
                "Generation cache hit",
                extra={"endpoint": "test_mcq", "cache_key": cache_key[:16], "model": MODEL},
            )
            return cached

    started = time.monotonic()
    prompt = f"""You are an educational assessment AI. Based on the following study material,
generate ONE conceptual multiple-choice question (MCQ) that tests deep understanding
(not simple recall). The question should require the student to apply, analyze, or
connect concepts.

The student is currently studying this subsection:
- subsection_id: "{target_sub["id"]}"
- title: "{target_sub["title"]}"

Generate the MCQ for THIS SUBSECTION ONLY.
Do NOT generate a question about any other subsection.

STUDY MATERIAL:
{context}{concept_focus_block}

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

RULES:
- Make all 4 options plausible (no obviously silly answers)
- The question should test understanding, NOT memorization
- Distractors should reflect common misconceptions
- Keep the question anchored to the target subsection only.{concept_rule}
- Return ONLY valid JSON, no markdown fences, no extra text."""

    try:
        data = _generate_json_with_retry(prompt, model=MODEL, retries=2)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate MCQ. The AI returned an invalid response. Please try again.",
        )

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
        "key_terms": data.get("key_terms", meta["key_terms"][:5]),
    }
    _generation_cache.set(cache_key, payload)
    _set_generation_cache_headers(response, "MISS", cache_key)
    logger.info(
        "Generation cache miss",
        extra={
            "endpoint": "test_mcq",
            "cache_key": cache_key[:16],
            "model": MODEL,
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
    """Evaluate an MCQ answer and return insights.
    If authenticated, auto-persists insights to Neo4j."""
    _set_no_store_headers(response)
    meta = _fetch_section_meta(section_id)
    context = meta["full_text"]
    source_id = body.subsection_id
    is_correct = body.selected == body.correct_answer

    # Build concept list for insight generation
    concept_list = "\n".join(
        f'  - concept_id: "{c["id"]}", name: "{c["name"]}"'
        for c in meta["concepts"]
    ) or "  (no concepts linked)"

    options_str = "\n".join(f"  {k}: {v}" for k, v in body.options.items())

    prompt = f"""You are an expert teacher evaluating a student's MCQ answer.

STUDY MATERIAL (ground truth):
{context}

QUESTION: {body.question}

OPTIONS:
{options_str}

CORRECT ANSWER: {body.correct_answer}: {body.options.get(body.correct_answer, '')}
STUDENT SELECTED: {body.selected}: {body.options.get(body.selected, '')}
IS CORRECT: {is_correct}

CONCEPTS LINKED TO THIS SECTION:
{concept_list}

─── TASK ───

Generate learning insights based on what the student's choice reveals about their understanding.

CRITICAL RULES:
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

    try:
        data = _generate_json_with_retry(prompt, model=EVAL_MODEL, retries=1)
    except Exception:
        data = {
            "feedback": "Correct!" if is_correct else "That's not quite right. Review the material and try again.",
            "explanation": "",
            "insights": [],
        }

    # Validate insights
    valid_concept_ids = {c["id"] for c in meta["concepts"]}
    insights = []
    for ins in data.get("insights", []):
        concept_id = ins.get("concept_id", "")
        ins_type = ins.get("type", "")
        ins_category = ins.get("category", "conceptual")
        if concept_id not in valid_concept_ids:
            continue
        if ins_type not in ("COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"):
            continue
        if ins_category not in ("conceptual", "mathematical"):
            continue
        insights.append({
            "concept_id": concept_id,
            "concept_name": ins.get("concept_name", ""),
            "type": ins_type,
            "category": ins_category,
            "content": ins.get("content", ""),
            "source_id": source_id,
        })

    # Auto-persist insights in the background so evaluation response is not blocked.
    auth_header_present = bool(request.headers.get("authorization"))
    persistence_status = "skipped_no_insights"
    if user and insights:
        persistence_status = "queued"
        for ins in insights:
            background_tasks.add_task(_persist_insight_safe, user.student_id, dict(ins))
    elif not user:
        persistence_status = (
            "skipped_invalid_auth" if auth_header_present else "skipped_unauthenticated"
        )

    return {
        "section_id": section_id,
        "is_correct": is_correct,
        "selected": body.selected,
        "correct_answer": body.correct_answer,
        "feedback": data.get("feedback", ""),
        "explanation": data.get("explanation", ""),
        "insights": insights,
        "persistence_status": persistence_status,
    }


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
    """Evaluate chapter-end exercise answers (text or image) and persist reconciled insights."""
    _set_no_store_headers(response)
    meta = _fetch_section_meta(section_id)
    context = meta["full_text"]
    source_id = section_id

    answer_text = (body.answer_text or "").strip()
    answer_images = body.answer_images or []
    if body.answer_mode == "text" and not answer_text:
        raise HTTPException(status_code=400, detail="answer_text is required for text mode")
    if body.answer_mode == "image" and not answer_images:
        raise HTTPException(status_code=400, detail="answer_images is required for image mode")

    concept_list = "\n".join(
        f'  - concept_id: "{c["id"]}", name: "{c["name"]}"'
        for c in meta["concepts"]
    ) or "  (no concepts linked)"

    answer_block = (
        f"STUDENT ANSWER (TEXT): {answer_text}"
        if body.answer_mode == "text"
        else f"STUDENT ANSWER: {len(answer_images)} handwritten image(s) attached."
    )
    input_mode_line = "INPUT MODE: IMAGE" if body.answer_mode == "image" else "INPUT MODE: TEXT"

    prompt = f"""You are an expert physics teacher evaluating a student's chapter-end exercise response.

STUDY MATERIAL (ground truth):
{context}

EXERCISE ID: {body.exercise_id}
EXERCISE QUESTION:
{body.problem}

{input_mode_line}
{answer_block}

CONCEPTS LINKED TO THIS SECTION:
{concept_list}

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

    try:
        data = _generate_gemini_json_with_retry(
            prompt,
            model=EXERCISE_EVAL_MODEL,
            image_data_urls=answer_images if body.answer_mode == "image" else None,
            retries=2,
        )
    except Exception:
        data = {
            "score": 50,
            "grade": "C",
            "feedback": "Could not fully evaluate. Please try again.",
            "strengths": [],
            "improvements": ["Try providing clearer step-by-step reasoning."],
            "model_answer": "",
            "insights": [],
        }

    valid_concept_ids = {c["id"] for c in meta["concepts"]}
    insights = []
    for ins in data.get("insights", []):
        concept_id = ins.get("concept_id", "")
        ins_type = ins.get("type", "")
        ins_category = ins.get("category", "conceptual")
        if concept_id not in valid_concept_ids:
            continue
        if ins_type not in ("COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"):
            continue
        if ins_category not in ("conceptual", "mathematical"):
            continue
        insights.append({
            "concept_id": concept_id,
            "concept_name": ins.get("concept_name", ""),
            "type": ins_type,
            "category": ins_category,
            "content": ins.get("content", ""),
            "source_id": source_id,
        })

    auth_header_present = bool(request.headers.get("authorization"))
    persistence_status = "skipped_no_insights"
    if user and insights:
        persistence_status = "queued"
        for ins in insights:
            background_tasks.add_task(_persist_insight_safe, user.student_id, dict(ins))
    elif not user:
        persistence_status = (
            "skipped_invalid_auth" if auth_header_present else "skipped_unauthenticated"
        )

    return {
        "section_id": section_id,
        "exercise_id": body.exercise_id,
        "model": EXERCISE_EVAL_MODEL,
        "answer_mode": body.answer_mode,
        "score": data.get("score", 0),
        "grade": data.get("grade", ""),
        "feedback": data.get("feedback", ""),
        "strengths": data.get("strengths", []),
        "improvements": data.get("improvements", []),
        "model_answer": data.get("model_answer", ""),
        "insights": insights,
        "persistence_status": persistence_status,
    }
