"""
Curriculum API — course structure (public) + knowledge graph (public; insights overlay if authenticated).

Routes:
  GET /api/grades                                      → available grades
  GET /api/grades/{grade}/subjects                     → subjects for a grade
  GET /api/grades/{grade}/subjects/{subject}/chapters  → chapters
  GET /api/chapters/{chapter_id:path}/sections         → sections for a chapter
  GET /api/chapters/{chapter_id:path}/graph            → knowledge graph (insights overlay if auth'd)
"""

import re
import time

from fastapi import APIRouter, Depends, HTTPException, Response, Query

from app.auth import get_optional_user
from app.config import settings
from app.database import read_query

router = APIRouter(prefix="/api", tags=["curriculum"])
_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL_SECONDS = 3600.0
_PUBLIC_BROWSER_CACHE_SECONDS = 86400
_PUBLIC_EDGE_CACHE_SECONDS = 2592000


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "untitled"


def _chapter_cover_url(grade: int, subject: str, chapter_number: int | str, chapter_title: str) -> str:
    try:
        chapter_num = int(chapter_number)
    except (TypeError, ValueError):
        chapter_num = 0
    domain = settings.CHAPTER_COVERS_ASSETS_DOMAIN.rstrip("/")
    prefix = settings.CHAPTER_COVERS_PREFIX.strip("/")
    subject_slug = _slugify(subject)
    title_slug = _slugify(chapter_title)
    return (
        f"{domain}/{prefix}/grade-{grade}/{subject_slug}/"
        f"chapter-{chapter_num:02d}-{title_slug}.jpg"
    )


def _set_public_cache_headers(
    response: Response,
    browser_seconds: int = _PUBLIC_BROWSER_CACHE_SECONDS,
    edge_seconds: int = _PUBLIC_EDGE_CACHE_SECONDS,
) -> None:
    # Browser gets a short TTL; CDN/edge gets longer TTL.
    response.headers["Cache-Control"] = (
        f"public, max-age={browser_seconds}, s-maxage={edge_seconds}, stale-while-revalidate=604800"
    )
    response.headers["CDN-Cache-Control"] = (
        f"public, max-age={edge_seconds}, stale-while-revalidate=604800"
    )


def _set_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["CDN-Cache-Control"] = "no-store"


def _cache_get(key: str):
    row = _cache.get(key)
    if not row:
        return None
    ts, payload = row
    if (time.time() - ts) > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return payload


def _cache_set(key: str, payload):
    _cache[key] = (time.time(), payload)


# ─── Grades ──────────────────────────────────────────────────────────
@router.get("/grades")
async def list_grades(response: Response):
    """Return available grade levels derived from Textbook nodes."""
    _set_public_cache_headers(response)
    key = "grades"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = read_query("""
        MATCH (t:Textbook)-[:CONTAINS]->(ch:Chapter)
        WITH t.grade AS grade, t.id AS tid, count(ch) AS ch_count
        WITH grade, sum(ch_count) AS chapter_count, collect(tid)[0] AS textbook_id
        RETURN grade,
               "Class " + toString(grade) AS label,
               chapter_count,
               textbook_id
        ORDER BY grade
    """)

    if not rows:
        raise HTTPException(status_code=404, detail="No grades found")
    _cache_set(key, rows)
    return rows


# ─── Subjects ────────────────────────────────────────────────────────
@router.get("/grades/{grade}/subjects")
async def list_subjects(grade: int, response: Response):
    """Return subjects available for a grade."""
    _set_public_cache_headers(response)
    key = f"subjects|{grade}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = read_query("""
        MATCH (s:Subject)-[:CONTAINS]->(t:Textbook {grade: $grade})
        OPTIONAL MATCH (t)-[:CONTAINS]->(ch:Chapter)
        WITH s, t, count(ch) AS chapter_count
        RETURN s.id AS id,
               s.name AS name,
               t.id AS textbook_id,
               chapter_count
        ORDER BY s.name
    """, grade=grade)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No subjects found for grade {grade}")
    _cache_set(key, rows)
    return rows


# ─── Chapters ────────────────────────────────────────────────────────
@router.get("/grades/{grade}/subjects/{subject}/chapters")
async def list_chapters(grade: int, subject: str, response: Response):
    """Return chapters for a grade + subject combo."""
    _set_public_cache_headers(response)
    key = f"chapters|{grade}|{subject.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = read_query("""
        MATCH (t:Textbook {grade: $grade})<-[:CONTAINS]-(s:Subject {name: $subject})
        MATCH (t)-[:CONTAINS]->(ch:Chapter)
        OPTIONAL MATCH (ch)-[:CONTAINS]->(sec:Section)
        OPTIONAL MATCH (ch)-[:HAS_EXERCISE_SET]->(es:ExerciseSet)-[:CONTAINS]->(ex:Exercise)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(c1:Concept)
        OPTIONAL MATCH (ex)-[:TESTS]->(c2:Concept)
        WITH ch,
             count(DISTINCT sec) AS section_count,
             count(DISTINCT ex) AS exercise_count,
             count(DISTINCT c1) + count(DISTINCT c2) - count(DISTINCT CASE WHEN c1 = c2 THEN c1 END) AS concept_count
        RETURN ch.id AS id,
               ch.number AS number,
               ch.title AS title,
               ch.summary AS summary,
               section_count,
               exercise_count,
               concept_count
        ORDER BY ch.number
    """, grade=grade, subject=subject)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No chapters found for grade {grade}, {subject}",
        )
    for row in rows:
        row["cover_image_url"] = _chapter_cover_url(
            grade=grade,
            subject=subject,
            chapter_number=row.get("number"),
            chapter_title=row.get("title", ""),
        )
    _cache_set(key, rows)
    return rows


# ─── Sections ────────────────────────────────────────────────────────
@router.get("/chapters/{chapter_id:path}/sections")
async def list_sections(chapter_id: str, response: Response):
    """Return sections for a chapter, with subsection + prerequisite counts."""
    _set_public_cache_headers(response)
    key = f"sections|{chapter_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = read_query("""
        MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
        OPTIONAL MATCH (sec)-[:CONTAINS]->(ss:Subsection)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(prereq)
        WITH sec, count(DISTINCT ss) AS subsection_count, count(DISTINCT prereq) AS prerequisite_count
        WITH sec, subsection_count, prerequisite_count,
             split(sec.number, '.') AS parts
        RETURN sec.id AS id,
               sec.number AS number,
               sec.title AS title,
               subsection_count,
               prerequisite_count
        ORDER BY toInteger(parts[0]), coalesce(toInteger(parts[1]), -1), coalesce(toInteger(parts[2]), -1)
    """, chapter_id=chapter_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No sections found for {chapter_id}")
    _cache_set(key, rows)
    return rows


# ─── Subsections ─────────────────────────────────────────────────────
@router.get("/sections/{section_id:path}/subsections")
async def list_subsections(section_id: str, response: Response):
    """Return subsections with their content for a section."""
    _set_public_cache_headers(response)
    key = f"subsections|{section_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = read_query("""
        MATCH (sec:Section {id: $section_id})-[:CONTAINS]->(ss:Subsection)
        OPTIONAL MATCH (ss)-[:HAS_WORKED_EXAMPLE]->(we:WorkedExample)
        OPTIONAL MATCH (ss)-[:HAS_DIAGRAM]->(d:Diagram)
        OPTIONAL MATCH (ss)-[:HAS_TABLE]->(tbl:Table)
        WITH ss,
             collect(DISTINCT {label: we.label, problem: we.problem, solution: we.solution}) AS worked_examples,
             collect(DISTINCT {label: d.label, description: d.description}) AS diagrams,
             collect(DISTINCT {caption: tbl.caption, headers: tbl.headers, rows_json: tbl.rows_json}) AS tables
        RETURN ss.id AS id,
               ss.number AS number,
               ss.title AS title,
               ss.content_text AS content,
               ss.content_type AS content_type,
               worked_examples,
               diagrams,
               tables
        ORDER BY ss.order
    """, section_id=section_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No subsections found for {section_id}")
    _cache_set(key, rows)
    return rows


# ─── Exercises for a Section ──────────────────────────────────────────
@router.get("/sections/{section_id:path}/exercises")
async def list_section_exercises(section_id: str, response: Response):
    """Return exercises that test a section (via TESTS relationship)."""
    _set_public_cache_headers(response)
    key = f"section_exercises|{section_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = read_query("""
        MATCH (e:Exercise)-[:TESTS]->(sec:Section {id: $section_id})
        OPTIONAL MATCH (es:ExerciseSet)-[:CONTAINS]->(e)
        RETURN e.id AS id,
               e.number AS number,
               e.problem AS problem,
               e.solution AS solution,
               e.difficulty AS difficulty,
               e.exercise_type AS exercise_type,
               es.title AS exercise_set
        ORDER BY e.number
    """, section_id=section_id)
    _cache_set(key, rows)
    return rows


# ─── Concepts for a Section ──────────────────────────────────────────
@router.get("/sections/{section_id:path}/concepts")
async def list_section_concepts(section_id: str, response: Response):
    """Return concepts related to a section (with animation URLs).

    Fetches:
      1. Concepts the section directly REQUIRES.
      2. Concepts from sections this section REQUIRES (one hop).
    Returns concepts that have a matching local animation file, or all
    concept assets when R2 animation hosting is configured.
    """
    _set_public_cache_headers(response)
    from pathlib import Path

    animations_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "animations"
    use_r2_assets = bool(settings.ANIMATIONS_R2_PUBLIC_BASE_URL)

    key = f"section_concepts|{section_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    rows = read_query("""
        MATCH (sec:Section {id: $section_id})
        OPTIONAL MATCH (sec)-[:REQUIRES]->(c:Concept)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(:Section)-[:REQUIRES]->(c2:Concept)
        WITH collect(DISTINCT c) + collect(DISTINCT c2) AS all_concepts
        UNWIND all_concepts AS concept
        WITH DISTINCT concept
        WHERE concept IS NOT NULL
        RETURN concept.id AS id, concept.name AS name
        ORDER BY concept.name
    """, section_id=section_id)

    seen_keys: set[str] = set()
    result = []

    for row in rows:
        concept_key = row["id"].replace("concept:", "")
        if concept_key in seen_keys:
            continue
        if not use_r2_assets:
            animation_file = animations_dir / f"{concept_key}.html"
            if not animation_file.exists():
                continue
        seen_keys.add(concept_key)
        result.append({
            "id": f"concept:{concept_key}",
            "name": (row["name"] or concept_key).replace("_", " ").title(),
            "concept_key": concept_key,
            "has_animation": True,
            "animation_type": "svg",
            "animation_url": f"/api/animations/{concept_key}.html",
        })

    _cache_set(key, result)
    return result


# ─── Knowledge Graph ─────────────────────────────────────────────────
@router.get("/chapters/{chapter_id:path}/graph")
async def chapter_graph(
    chapter_id: str,
    response: Response,
    user=Depends(get_optional_user),
):
    """
    Return nodes and edges for the chapter knowledge graph.

    Open to all (no auth required). If the student is authenticated,
    each node is annotated with their active insight for that node.

    Response includes:
      - nodes: list of section + concept nodes (with optional insight)
      - edges: NEXT and REQUIRES relationships
      - section_ids: for client-side insight filtering
      - concept_ids: for client-side insight filtering
    """
    # Protect auth-sensitive graph overlays from edge cache pollution.
    response.headers["Vary"] = "Authorization"
    if user:
        _set_no_store_headers(response)
    else:
        _set_public_cache_headers(response)

    # ── Nodes: sections + concepts ────────────────────────────────────
    node_rows = read_query("""
        MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(concept:Concept)
        WITH collect(DISTINCT {
            id:     sec.id,
            label:  sec.title,
            number: sec.number,
            type:   'section'
        }) AS section_nodes,
        collect(DISTINCT CASE WHEN concept IS NOT NULL THEN {
            id:    concept.id,
            label: concept.name,
            type:  'concept'
        } END) AS concept_nodes
        RETURN section_nodes,
               [c IN concept_nodes WHERE c IS NOT NULL] AS concept_nodes
    """, chapter_id=chapter_id)

    nodes: list[dict] = []
    section_ids: list[str] = []
    concept_ids: list[str] = []

    if node_rows:
        for n in node_rows[0].get("section_nodes", []):
            nodes.append(n)
            section_ids.append(n["id"])
        for n in node_rows[0].get("concept_nodes", []):
            nodes.append(n)
            concept_ids.append(n["id"])

    # ── Overlay insights if student is authenticated ───────────────────
    if user and (section_ids or concept_ids):
        insight_rows = read_query("""
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            WHERE any(sid IN $section_ids WHERE (i)-[:ABOUT_SOURCE]->(:Section {id: sid}))
               OR any(cid IN $concept_ids WHERE (i)-[:ABOUT_CONCEPT]->(:Concept {id: cid}))
            RETURN i.type                                              AS type,
                   i.category                                         AS category,
                   i.content                                          AS content,
                   i.created_at                                       AS created_at,
                   [(i)-[:ABOUT_SOURCE]->(src) | src.id][0]          AS source_id,
                   [(i)-[:ABOUT_CONCEPT]->(c)  | c.id][0]            AS concept_id
            ORDER BY i.created_at DESC
        """,
            student_id=user.student_id,
            section_ids=section_ids,
            concept_ids=concept_ids,
        )

        # Build lookup: node_id -> insight
        insight_by_node: dict[str, dict] = {}
        for row in insight_rows:
            if row.get("source_id") and row["source_id"] not in insight_by_node:
                insight_by_node[row["source_id"]] = {
                    "type": row["type"],
                    "category": row["category"],
                    "content": row["content"],
                }
            if row.get("concept_id") and row["concept_id"] not in insight_by_node:
                insight_by_node[row["concept_id"]] = {
                    "type": row["type"],
                    "category": row["category"],
                    "content": row["content"],
                }

        # Annotate nodes
        for node in nodes:
            node["insight"] = insight_by_node.get(node["id"])

    # ── Edges: NEXT + REQUIRES ────────────────────────────────────────
    edge_rows = read_query("""
        MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
        OPTIONAL MATCH (sec)-[n:NEXT]->(next_sec:Section)
        OPTIONAL MATCH (sec)-[r:REQUIRES]->(target)
        WITH collect(DISTINCT CASE WHEN next_sec IS NOT NULL
            THEN {source: sec.id, target: next_sec.id, type: 'NEXT'}
            END) AS next_edges,
        collect(DISTINCT CASE WHEN target IS NOT NULL
            THEN {source: sec.id, target: target.id, type: 'REQUIRES'}
            END) AS req_edges
        RETURN [e IN next_edges + req_edges WHERE e IS NOT NULL] AS edges
    """, chapter_id=chapter_id)

    return {
        "nodes": nodes,
        "edges": edge_rows[0]["edges"] if edge_rows else [],
        "section_ids": section_ids,
        "concept_ids": concept_ids,
    }


@router.get("/concepts/{concept_id:path}/lineage")
async def concept_lineage(
    concept_id: str,
    response: Response,
    chapter_limit: int = Query(default=60, ge=1, le=60),
):
    """
    Return cross-curriculum lineage graph for a concept:
      concept -> grades -> subjects -> chapters
    """
    _set_public_cache_headers(response)
    # Version cache key so stale pre-fix lineage payloads are not reused.
    key = f"concept_lineage:v2|{concept_id}|{chapter_limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    concept_rows = read_query(
        """
        MATCH (c:Concept {id: $concept_id})
        RETURN c.id AS id, c.name AS name
        LIMIT 1
        """,
        concept_id=concept_id,
    )
    if not concept_rows:
        raise HTTPException(status_code=404, detail="Concept not found")

    chapter_rows = read_query(
        """
        MATCH (c:Concept {id: $concept_id})
        OPTIONAL MATCH (sec:Section)-[:REQUIRES]->(c)
        OPTIONAL MATCH (ch_from_sec:Chapter)-[:CONTAINS]->(sec)
        OPTIONAL MATCH (ex:Exercise)-[:TESTS]->(c)
        OPTIONAL MATCH (es:ExerciseSet)-[:CONTAINS]->(ex)
        OPTIONAL MATCH (ch_from_ex:Chapter)-[:HAS_EXERCISE_SET]->(es)
        WITH c, collect(DISTINCT ch_from_sec) + collect(DISTINCT ch_from_ex) AS chapters
        UNWIND chapters AS ch
        WITH DISTINCT c, ch
        WHERE ch IS NOT NULL
        MATCH (t:Textbook)-[:CONTAINS]->(ch)
        MATCH (s:Subject)-[:CONTAINS]->(t)
        RETURN t.grade AS grade,
               s.name AS subject_name,
               ch.id AS chapter_id,
               ch.number AS chapter_number,
               ch.title AS chapter_title
        ORDER BY toInteger(t.grade), s.name, toInteger(ch.number), ch.number, ch.title
        """,
        concept_id=concept_id,
    )

    chapter_total = len(chapter_rows)
    limited_rows = chapter_rows[:chapter_limit]
    truncated = chapter_total > chapter_limit

    concept = {
        "id": concept_rows[0]["id"],
        "name": (concept_rows[0].get("name") or concept_rows[0]["id"]).replace("_", " ").title(),
    }

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    concept_node_id = concept["id"]
    nodes.append({"id": concept_node_id, "type": "concept", "label": concept["name"], "meta": {}})
    seen_nodes.add(concept_node_id)

    def add_node(node_id: str, node_type: str, label: str, meta: dict):
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append({"id": node_id, "type": node_type, "label": label, "meta": meta})

    def add_edge(source: str, target: str, edge_type: str = "HAS"):
        key_edge = (source, target, edge_type)
        if key_edge in seen_edges:
            return
        seen_edges.add(key_edge)
        edges.append({"source": source, "target": target, "type": edge_type})

    for row in limited_rows:
        grade = str(row.get("grade", ""))
        subject_name = str(row.get("subject_name", "")).strip()
        chapter_id = str(row.get("chapter_id", "")).strip()
        chapter_number = str(row.get("chapter_number", "")).strip()
        chapter_title = str(row.get("chapter_title", "")).strip()
        if not grade or not subject_name or not chapter_id or not chapter_number:
            continue

        grade_node_id = f"grade:{grade}"
        subject_slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in subject_name).strip("-")
        while "--" in subject_slug:
            subject_slug = subject_slug.replace("--", "-")
        # Subject nodes must be grade-scoped to avoid collapsing
        # Grade 11 Physics and Grade 12 Physics into one node.
        subject_node_id = f"subject:{grade}:{subject_slug}"
        chapter_node_id = f"chapter:{chapter_id}"

        add_node(grade_node_id, "grade", f"Class {grade}", {"grade": grade})
        add_node(
            subject_node_id,
            "subject",
            subject_name,
            {
                "subject_name": subject_name,
                "subject_slug": subject_slug,
            },
        )
        add_node(
            chapter_node_id,
            "chapter",
            f"{chapter_number}. {chapter_title}" if chapter_title else chapter_number,
            {
                "grade": grade,
                "subject_name": subject_name,
                "subject_slug": subject_slug,
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
            },
        )

        add_edge(concept_node_id, grade_node_id)
        add_edge(grade_node_id, subject_node_id)
        add_edge(subject_node_id, chapter_node_id)

    payload = {
        "concept": concept,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "chapter_total": chapter_total,
            "chapter_returned": len([n for n in nodes if n.get("type") == "chapter"]),
            "limit": chapter_limit,
            "truncated": truncated,
        },
    }
    _cache_set(key, payload)
    return payload
