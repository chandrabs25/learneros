"""
Curriculum API — course structure (public) + knowledge graph (public; insights overlay if authenticated).

Routes:
  GET /api/grades                                      → available grades
  GET /api/grades/{grade}/subjects                     → subjects for a grade
  GET /api/grades/{grade}/subjects/{subject}/chapters  → chapters
  GET /api/chapters/{chapter_id:path}/sections         → sections for a chapter
  GET /api/chapters/{chapter_id:path}/graph            → knowledge graph (insights overlay if auth'd)
"""

import time

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_optional_user
from app.database import read_query

router = APIRouter(prefix="/api", tags=["curriculum"])
_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL_SECONDS = 60.0


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
async def list_grades():
    """Return available grade levels derived from Textbook nodes."""
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
async def list_subjects(grade: int):
    """Return subjects available for a grade."""
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
async def list_chapters(grade: int, subject: str):
    """Return chapters for a grade + subject combo."""
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
    _cache_set(key, rows)
    return rows


# ─── Sections ────────────────────────────────────────────────────────
@router.get("/chapters/{chapter_id:path}/sections")
async def list_sections(chapter_id: str):
    """Return sections for a chapter, with subsection + prerequisite counts."""
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
async def list_subsections(section_id: str):
    """Return subsections with their content for a section."""
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
async def list_section_exercises(section_id: str):
    """Return exercises that test a section (via TESTS relationship)."""
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
async def list_section_concepts(section_id: str):
    """Return concepts related to a section (with animation URLs).

    Fetches:
      1. Concepts the section directly REQUIRES.
      2. Concepts from sections this section REQUIRES (one hop).
    Only returns concepts that have a matching animation file.
    """
    from pathlib import Path

    animations_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "animations"

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
        animation_file = animations_dir / f"{concept_key}.html"
        if not animation_file.exists():
            continue
        seen_keys.add(concept_key)
        result.append({
            "id": f"concept:{concept_key}",
            "name": (row["name"] or concept_key).replace("_", " ").title(),
            "concept_key": concept_key,
            "has_animation": True,
            "animation_url": f"/api/animations/{concept_key}.html",
        })

    _cache_set(key, result)
    return result


# ─── Knowledge Graph ─────────────────────────────────────────────────
@router.get("/chapters/{chapter_id:path}/graph")
async def chapter_graph(
    chapter_id: str,
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
