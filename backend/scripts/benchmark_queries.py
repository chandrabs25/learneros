"""
Neo4j Query Latency Benchmark for Student-Facing Endpoints
===========================================================

Runs all student-facing Cypher queries against the configured Neo4j database,
measures latency percentiles, and optionally PROFILEs for db hits / index usage.

Usage:
  cd backend
  uv run python scripts/benchmark_queries.py --student-id <id> --section-id <id>
  uv run python scripts/benchmark_queries.py --student-id <id> --section-id <id> --profile
  uv run python scripts/benchmark_queries.py --discover          # auto-find test params
  uv run python scripts/benchmark_queries.py --router tutor      # only tutor queries
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.config import settings  # noqa: E402
from app.database import get_driver  # noqa: E402


# ── Query Definition ──────────────────────────────────────────────────────

@dataclass
class BenchQuery:
    name: str
    router: str          # curriculum | test | tutor | insights
    qtype: str           # read | write
    cypher: str
    params: dict[str, Any] = field(default_factory=dict)
    hot: bool = False    # True if called on every page load / interaction
    note: str = ""       # suspected issue
    skip: bool = False   # skip write queries by default


def build_queries(
    student_id: str,
    section_id: str,
    subsection_id: str,
    chapter_id: str,
    concept_id: str,
    session_id: str,
    grade: int,
    subject: str,
) -> list[BenchQuery]:
    """Build all 28+ student-facing queries with realistic params."""

    return [
        # ═══ CURRICULUM ═══════════════════════════════════════════════════

        BenchQuery(
            name="list_grades",
            router="curriculum",
            qtype="read",
            hot=True,
            cypher="""
            MATCH (t:Textbook)-[:CONTAINS]->(ch:Chapter)
            WITH t.grade AS grade, t.id AS tid, count(ch) AS ch_count
            WITH grade, sum(ch_count) AS chapter_count, collect(tid)[0] AS textbook_id
            RETURN grade,
                   "Class " + toString(grade) AS label,
                   chapter_count,
                   textbook_id
            ORDER BY grade
            """,
        ),

        BenchQuery(
            name="list_subjects",
            router="curriculum",
            qtype="read",
            hot=True,
            cypher="""
            MATCH (s:Subject)-[:CONTAINS]->(t:Textbook {grade: $grade})
            OPTIONAL MATCH (t)-[:CONTAINS]->(ch:Chapter)
            WITH s, t, count(ch) AS chapter_count
            RETURN s.id AS id,
                   s.name AS name,
                   t.id AS textbook_id,
                   chapter_count
            ORDER BY s.name
            """,
            params={"grade": grade},
        ),

        BenchQuery(
            name="list_chapters",
            router="curriculum",
            qtype="read",
            hot=True,
            note="4× OPTIONAL MATCH with concept dedup",
            cypher="""
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
                   section_count,
                   exercise_count,
                   concept_count
            ORDER BY ch.number
            """,
            params={"grade": grade, "subject": subject},
        ),

        BenchQuery(
            name="list_sections",
            router="curriculum",
            qtype="read",
            hot=True,
            cypher="""
            MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
            OPTIONAL MATCH (sec)-[:CONTAINS]->(ss:Subsection)
            OPTIONAL MATCH (sec)-[:REQUIRES]->(prereq)
            WITH sec, count(DISTINCT ss) AS subsection_count, count(DISTINCT prereq) AS prerequisite_count,
                 split(sec.number, '.') AS parts
            RETURN sec.id AS id,
                   sec.number AS number,
                   sec.title AS title,
                   subsection_count,
                   prerequisite_count
            ORDER BY toInteger(parts[0]), coalesce(toInteger(parts[1]), -1)
            """,
            params={"chapter_id": chapter_id},
        ),

        BenchQuery(
            name="list_subsections",
            router="curriculum",
            qtype="read",
            hot=True,
            note="3× OPTIONAL MATCH for worked examples, diagrams, tables",
            cypher="""
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
            """,
            params={"section_id": section_id},
        ),

        BenchQuery(
            name="list_section_exercises",
            router="curriculum",
            qtype="read",
            cypher="""
            MATCH (e:Exercise)-[:TESTS]->(sec:Section {id: $section_id})
            OPTIONAL MATCH (es:ExerciseSet)-[:CONTAINS]->(e)
            RETURN e.id AS id,
                   e.number AS number,
                   e.problem AS problem,
                   e.difficulty AS difficulty,
                   es.title AS exercise_set
            ORDER BY e.number
            """,
            params={"section_id": section_id},
        ),

        BenchQuery(
            name="list_section_concepts",
            router="curriculum",
            qtype="read",
            cypher="""
            MATCH (sec:Section {id: $section_id})
            OPTIONAL MATCH (sec)-[:REQUIRES]->(c:Concept)
            OPTIONAL MATCH (sec)-[:REQUIRES]->(:Section)-[:REQUIRES]->(c2:Concept)
            WITH collect(DISTINCT c) + collect(DISTINCT c2) AS all_concepts
            UNWIND all_concepts AS concept
            WITH DISTINCT concept
            WHERE concept IS NOT NULL
            RETURN concept.id AS id, concept.name AS name
            ORDER BY concept.name
            """,
            params={"section_id": section_id},
        ),

        BenchQuery(
            name="knowledge_graph_nodes_edges_BATCHED",
            router="curriculum",
            qtype="read",
            note="BATCHED: nodes + edges in 1 query (was 2)",
            cypher="""
            MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
            OPTIONAL MATCH (sec)-[:REQUIRES]->(concept:Concept)
            OPTIONAL MATCH (sec)-[:NEXT]->(next_sec:Section)
            OPTIONAL MATCH (sec)-[:REQUIRES]->(target)
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
            } END) AS concept_nodes,
            collect(DISTINCT CASE WHEN next_sec IS NOT NULL
                THEN {source: sec.id, target: next_sec.id, type: 'NEXT'}
                END) AS next_edges,
            collect(DISTINCT CASE WHEN target IS NOT NULL
                THEN {source: sec.id, target: target.id, type: 'REQUIRES'}
                END) AS req_edges
            RETURN section_nodes,
                   [c IN concept_nodes WHERE c IS NOT NULL] AS concept_nodes,
                   [e IN next_edges + req_edges WHERE e IS NOT NULL] AS edges
            """,
            params={"chapter_id": chapter_id},
        ),

        BenchQuery(
            name="knowledge_graph_insights_overlay",
            router="curriculum",
            qtype="read",
            note="any() list comprehensions in WHERE — expensive on large graphs",
            cypher="""
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            WHERE any(sid IN $section_ids WHERE (i)-[:ABOUT_SOURCE]->(:Section {id: sid}))
               OR any(cid IN $concept_ids WHERE (i)-[:ABOUT_CONCEPT]->(:Concept {id: cid}))
            RETURN i.type AS type,
                   i.category AS category,
                   i.content AS content,
                   [(i)-[:ABOUT_SOURCE]->(src) | src.id][0] AS source_id,
                   [(i)-[:ABOUT_CONCEPT]->(c)  | c.id][0] AS concept_id
            ORDER BY i.created_at DESC
            """,
            params={"student_id": student_id, "section_ids": [section_id], "concept_ids": [concept_id]},
        ),

        BenchQuery(
            name="concept_lineage_BATCHED",
            router="curriculum",
            qtype="read",
            note="BATCHED: concept lookup + chapter traversal in 1 query (was 2)",
            cypher="""
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
            RETURN c.id AS concept_id,
                   c.name AS concept_name,
                   t.grade AS grade,
                   s.name AS subject_name,
                   ch.id AS chapter_id,
                   ch.number AS chapter_number,
                   ch.title AS chapter_title
            ORDER BY toInteger(t.grade), s.name, toInteger(ch.number)
            """,
            params={"concept_id": concept_id},
        ),

        # ═══ TEST ═════════════════════════════════════════════════════════

        BenchQuery(
            name="fetch_section_meta_BATCHED",
            router="test",
            qtype="read",
            hot=True,
            note="BATCHED: subsections + concepts in 1 query (was 2)",
            cypher="""
            MATCH (sec:Section {id: $section_id})-[:CONTAINS]->(ss:Subsection)
            WITH sec, ss ORDER BY ss.order
            WITH sec,
                 collect({sub_id: ss.id, sub_title: ss.title, content: ss.content_text}) AS subsections
            MATCH (sec)<-[:CONTAINS]-(ch:Chapter)-[:CONTAINS]->(sec2:Section)
            OPTIONAL MATCH (sec2)-[:CONTAINS]->(:Subsection)-[:REQUIRES]->(c_sub:Concept)
            OPTIONAL MATCH (sec2)-[:REQUIRES]->(c_sec:Concept)
            WITH sec, subsections,
                 collect(DISTINCT c_sub) + collect(DISTINCT c_sec) AS all_concepts
            UNWIND (CASE WHEN size(all_concepts) = 0 THEN [null] ELSE all_concepts END) AS c
            WITH sec, subsections,
                 collect(DISTINCT CASE WHEN c IS NOT NULL THEN {id: c.id, name: c.name} END) AS raw_concepts
            RETURN sec.title AS section_title,
                   subsections,
                   [x IN raw_concepts WHERE x IS NOT NULL] AS concepts
            """,
            params={"section_id": section_id},
        ),

        BenchQuery(
            name="find_active_insights_for_reconcile",
            router="test",
            qtype="read",
            hot=True,
            cypher="""
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true, category: $category})
                  -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
            WHERE (i)-[:ABOUT_SOURCE]->({id: $source_id})
            RETURN i.id AS id, i.type AS type, i.content AS content, i.created_at AS created_at
            ORDER BY i.created_at DESC
            """,
            params={
                "student_id": student_id,
                "concept_id": concept_id,
                "source_id": subsection_id,
                "category": "conceptual",
            },
        ),

        # ═══ TUTOR ════════════════════════════════════════════════════════

        BenchQuery(
            name="fetch_subsection_context",
            router="tutor",
            qtype="read",
            hot=True,
            cypher="""
            MATCH (sec:Section {id: $section_id})-[:CONTAINS]->(ss:Subsection)
            RETURN sec.title AS section_title,
                   ss.id AS id,
                   ss.title AS title,
                   ss.content_text AS content,
                   ss.order AS ord
            ORDER BY ss.order
            """,
            params={"section_id": section_id},
        ),

        BenchQuery(
            name="vector_insight_search",
            router="tutor",
            qtype="read",
            hot=True,
            note="Vector index scans ALL students' insights, then post-filters",
            cypher="""
            CALL db.index.vector.queryNodes('insight_embedding_index', $n, $embedding)
            YIELD node, score
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(node)
            WHERE node.is_active = true
            OPTIONAL MATCH (node)-[:ABOUT_CONCEPT]->(c:Concept)
            OPTIONAL MATCH (node)-[:ABOUT_SOURCE]->(src)
            RETURN node.id AS id,
                   node.type AS type,
                   node.category AS category,
                   node.content AS content,
                   node.is_active AS is_active,
                   c.id AS concept_id,
                   c.name AS concept_name,
                   src.id AS source_id,
                   src.title AS source_title,
                   score AS similarity
            ORDER BY score DESC
            LIMIT $k
            """,
            params={"student_id": student_id, "n": 20, "k": 5, "embedding": "__NEEDS_EMBEDDING__"},
            skip=True,  # Needs real embedding vector — handled separately
        ),

        BenchQuery(
            name="load_conversation_history",
            router="tutor",
            qtype="read",
            hot=True,
            cypher="""
            MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession {id: $session_id})
                  -[:HAS_MESSAGE]->(m:TutorMessage)
            RETURN m.role AS role, m.content AS content
            ORDER BY m.created_at ASC
            LIMIT $limit
            """,
            params={"student_id": student_id, "session_id": session_id, "limit": 12},
        ),

        BenchQuery(
            name="latest_global_session_id",
            router="tutor",
            qtype="read",
            hot=True,
            note="No index on TutorSession.mode",
            cypher="""
            MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession)
            WHERE sess.mode = 'global'
            RETURN sess.id AS id
            ORDER BY coalesce(sess.updated_at, sess.created_at) DESC
            LIMIT 1
            """,
            params={"student_id": student_id},
        ),

        BenchQuery(
            name="latest_subsection_session_id",
            router="tutor",
            qtype="read",
            cypher="""
            MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession)
            WHERE sess.section_id = $section_id AND sess.subsection_id = $subsection_id
            RETURN sess.id AS id
            ORDER BY coalesce(sess.updated_at, sess.created_at) DESC
            LIMIT 1
            """,
            params={"student_id": student_id, "section_id": section_id, "subsection_id": subsection_id},
        ),

        BenchQuery(
            name="list_global_sessions",
            router="tutor",
            qtype="read",
            hot=True,
            note="No index on TutorSession.mode; subquery collects first message",
            cypher="""
            MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession)
            WHERE sess.mode = 'global'
            OPTIONAL MATCH (sess)-[:HAS_MESSAGE]->(m:TutorMessage {role: 'user'})
            WITH sess, m ORDER BY m.created_at ASC
            WITH sess, collect(m.content)[0] AS first_msg
            RETURN sess.id AS id,
                   coalesce(first_msg, '') AS preview,
                   toString(sess.created_at) AS created_at,
                   toString(coalesce(sess.updated_at, sess.created_at)) AS updated_at
            ORDER BY coalesce(sess.updated_at, sess.created_at) DESC
            LIMIT 30
            """,
            params={"student_id": student_id},
        ),

        # ═══ INSIGHTS ═════════════════════════════════════════════════════

        BenchQuery(
            name="get_insight_context",
            router="insights",
            qtype="read",
            cypher="""
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
            params={"student_id": student_id, "insight_id": "insight:placeholder"},
        ),

        BenchQuery(
            name="list_active_insights_all",
            router="insights",
            qtype="read",
            hot=True,
            cypher="""
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
            """,
            params={"student_id": student_id},
        ),

        BenchQuery(
            name="active_insights_by_subsection",
            router="insights",
            qtype="read",
            hot=True,
            cypher="""
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
            params={"student_id": student_id, "subsection_id": subsection_id},
        ),

        BenchQuery(
            name="concept_insight_log",
            router="insights",
            qtype="read",
            cypher="""
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
            params={"student_id": student_id, "concept_id": concept_id},
        ),
    ]


# ── Auto-discover realistic test params ───────────────────────────────────

def discover_params(driver) -> dict[str, Any]:
    """Pull real IDs from the database for benchmarking."""
    print("  🔍 Auto-discovering test parameters from database...")
    params: dict[str, Any] = {}

    with driver.session() as sess:
        # Find a grade + subject
        rows = sess.execute_read(lambda tx: list(tx.run(
            "MATCH (s:Subject)-[:CONTAINS]->(t:Textbook) RETURN t.grade AS grade, s.name AS subject LIMIT 1"
        )))
        if rows:
            params["grade"] = rows[0]["grade"]
            params["subject"] = rows[0]["subject"]

        # Find a chapter
        rows = sess.execute_read(lambda tx: list(tx.run(
            "MATCH (ch:Chapter) RETURN ch.id AS id LIMIT 1"
        )))
        if rows:
            params["chapter_id"] = rows[0]["id"]

        # Find a section with subsections
        rows = sess.execute_read(lambda tx: list(tx.run(
            "MATCH (sec:Section)-[:CONTAINS]->(ss:Subsection) RETURN sec.id AS sec_id, ss.id AS ss_id LIMIT 1"
        )))
        if rows:
            params["section_id"] = rows[0]["sec_id"]
            params["subsection_id"] = rows[0]["ss_id"]

        # Find a concept
        rows = sess.execute_read(lambda tx: list(tx.run(
            "MATCH (c:Concept) RETURN c.id AS id LIMIT 1"
        )))
        if rows:
            params["concept_id"] = rows[0]["id"]

        # Find a student with insights
        rows = sess.execute_read(lambda tx: list(tx.run(
            "MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true}) RETURN s.id AS id, count(i) AS cnt ORDER BY cnt DESC LIMIT 1"
        )))
        if rows:
            params["student_id"] = rows[0]["id"]
            print(f"     Student: {rows[0]['id']} ({rows[0]['cnt']} active insights)")

        # Find a tutor session
        rows = sess.execute_read(lambda tx: list(tx.run(
            "MATCH (s:Student)-[:HAS_TUTOR_SESSION]->(sess:TutorSession)-[:HAS_MESSAGE]->(m:TutorMessage) "
            "RETURN sess.id AS id LIMIT 1"
        )))
        if rows:
            params["session_id"] = rows[0]["id"]

    return params


# ── Benchmark Runner ──────────────────────────────────────────────────────

def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[-1]
    return data[f] + (k - f) * (data[c] - data[f])


@dataclass
class QueryResult:
    query: BenchQuery
    timings_ms: list[float]
    rows_returned: int
    db_hits: int | None = None
    plan_summary: str = ""
    error: str = ""

    @property
    def p50(self) -> float:
        s = sorted(self.timings_ms)
        return percentile(s, 50)

    @property
    def p95(self) -> float:
        s = sorted(self.timings_ms)
        return percentile(s, 95)

    @property
    def max_ms(self) -> float:
        return max(self.timings_ms) if self.timings_ms else 0.0

    @property
    def flag(self) -> str:
        if self.error:
            return "❌ ERROR"
        if self.p95 > 50:
            return "🔴 SLOW"
        if self.p95 > 15:
            return "🟡 WARN"
        return "✅"


def run_benchmark(
    driver,
    queries: list[BenchQuery],
    runs: int = 5,
    do_profile: bool = False,
    do_warmup: bool = True,
) -> list[QueryResult]:
    results: list[QueryResult] = []

    for q in queries:
        if q.skip:
            results.append(QueryResult(
                query=q, timings_ms=[], rows_returned=0,
                error="SKIPPED (needs embedding vector)"
            ))
            continue

        # Warmup run
        if do_warmup:
            try:
                with driver.session() as sess:
                    if q.qtype == "read":
                        sess.execute_read(lambda tx: list(tx.run(q.cypher, **q.params)))
                    else:
                        sess.execute_read(lambda tx: list(tx.run(q.cypher, **q.params)))
            except Exception:
                pass

        # Timed runs
        timings: list[float] = []
        rows_count = 0
        error_msg = ""

        for i in range(runs):
            try:
                with driver.session() as sess:
                    start = time.perf_counter()
                    if q.qtype == "read":
                        rows = sess.execute_read(lambda tx: list(tx.run(q.cypher, **q.params)))
                    else:
                        # For write queries, use read transaction to avoid mutations
                        rows = sess.execute_read(lambda tx: list(tx.run(
                            "EXPLAIN " + q.cypher, **q.params
                        )))
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    timings.append(elapsed_ms)
                    if i == 0:
                        rows_count = len(rows)
            except Exception as e:
                error_msg = str(e)[:120]
                break

        # PROFILE run (optional)
        db_hits = None
        plan_summary = ""
        if do_profile and not error_msg and q.qtype == "read":
            try:
                with driver.session() as sess:
                    result = sess.run("PROFILE " + q.cypher, **q.params)
                    _ = list(result)  # consume results
                    summary = result.consume()
                    if summary.profile:
                        db_hits = summary.profile.get("dbHits", 0)

                        def _walk_plan(plan, depth=0):
                            parts = []
                            op = plan.get("operatorType", "?")
                            hits = plan.get("dbHits", 0)
                            r = plan.get("rows", 0)
                            parts.append(f"{'  ' * depth}{op} (dbHits={hits}, rows={r})")
                            for child in plan.get("children", []):
                                parts.extend(_walk_plan(child, depth + 1))
                            return parts

                        plan_lines = _walk_plan(summary.profile)
                        plan_summary = "\n".join(plan_lines[:12])  # cap at 12 lines
            except Exception as e:
                plan_summary = f"PROFILE failed: {str(e)[:80]}"

        results.append(QueryResult(
            query=q,
            timings_ms=timings,
            rows_returned=rows_count,
            db_hits=db_hits,
            plan_summary=plan_summary,
            error=error_msg,
        ))

    return results


# ── Output Formatting ─────────────────────────────────────────────────────

def print_results(results: list[QueryResult], do_profile: bool = False) -> None:
    routers = ["curriculum", "test", "tutor", "insights"]
    flagged: list[QueryResult] = []

    for router in routers:
        group = [r for r in results if r.query.router == router]
        if not group:
            continue

        print(f"\n  {'═' * 68}")
        print(f"  {router.upper()} QUERIES")
        print(f"  {'─' * 68}")

        for r in group:
            if r.error:
                print(f"  {r.query.name:<40} {r.flag}  {r.error}")
                if r.error != "SKIPPED (needs embedding vector)":
                    flagged.append(r)
                continue

            hot_marker = " 🔥" if r.query.hot else ""
            db_str = f"  dbHits={r.db_hits}" if r.db_hits is not None else ""
            note_str = f"  ← {r.query.note}" if r.query.note else ""

            print(
                f"  {r.query.name:<40} "
                f"p50: {r.p50:>6.1f}ms  "
                f"p95: {r.p95:>6.1f}ms  "
                f"max: {r.max_ms:>6.1f}ms  "
                f"rows: {r.rows_returned:<4} "
                f"{r.flag}{hot_marker}{db_str}{note_str}"
            )

            if do_profile and r.plan_summary:
                for line in r.plan_summary.split("\n"):
                    print(f"       │ {line}")

            if r.p95 > 15 or (r.db_hits is not None and r.db_hits > 1000):
                flagged.append(r)

    # Summary
    print(f"\n  {'═' * 68}")
    print(f"  SUMMARY")
    print(f"  {'─' * 68}")

    total = len([r for r in results if not r.error])
    slow = len([r for r in results if not r.error and r.p95 > 50])
    warn = len([r for r in results if not r.error and 15 < r.p95 <= 50])
    ok = total - slow - warn

    print(f"  Total: {total}  |  ✅ OK (<15ms): {ok}  |  🟡 WARN (15-50ms): {warn}  |  🔴 SLOW (>50ms): {slow}")

    if flagged:
        print(f"\n  {'─' * 68}")
        print(f"  FLAGGED QUERIES ({len(flagged)}):")
        for r in flagged:
            if r.error and "SKIP" not in r.error:
                print(f"    ❌ {r.query.name}: {r.error}")
            else:
                suggestion = ""
                if r.query.note:
                    suggestion = f" → {r.query.note}"
                hits_str = f", dbHits={r.db_hits}" if r.db_hits is not None else ""
                print(f"    ⚠️  {r.query.name}: p95={r.p95:.1f}ms{hits_str}{suggestion}")


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Neo4j Query Latency Benchmark")
    parser.add_argument("--student-id", default="", help="Student ID to use for insight queries")
    parser.add_argument("--section-id", default="", help="Section ID for content queries")
    parser.add_argument("--subsection-id", default="", help="Subsection ID (auto-resolved if missing)")
    parser.add_argument("--chapter-id", default="", help="Chapter ID (auto-resolved if missing)")
    parser.add_argument("--concept-id", default="", help="Concept ID (auto-resolved if missing)")
    parser.add_argument("--session-id", default="", help="Tutor session ID (auto-resolved if missing)")
    parser.add_argument("--grade", type=int, default=0, help="Grade number")
    parser.add_argument("--subject", default="", help="Subject name")
    parser.add_argument("--runs", type=int, default=5, help="Number of timed runs per query (default: 5)")
    parser.add_argument("--profile", action="store_true", help="Run PROFILE for db hits and query plans")
    parser.add_argument("--discover", action="store_true", help="Auto-discover params from database")
    parser.add_argument("--router", choices=["curriculum", "test", "tutor", "insights"], help="Only run queries from this router")

    args = parser.parse_args()

    driver = get_driver()

    # Auto-discover params if needed
    if args.discover or (not args.student_id and not args.section_id):
        discovered = discover_params(driver)
        if not args.student_id:
            args.student_id = discovered.get("student_id", "student:unknown")
        if not args.section_id:
            args.section_id = discovered.get("section_id", "")
        if not args.subsection_id:
            args.subsection_id = discovered.get("subsection_id", "")
        if not args.chapter_id:
            args.chapter_id = discovered.get("chapter_id", "")
        if not args.concept_id:
            args.concept_id = discovered.get("concept_id", "")
        if not args.session_id:
            args.session_id = discovered.get("session_id", "")
        if not args.grade:
            args.grade = discovered.get("grade", 9)
        if not args.subject:
            args.subject = discovered.get("subject", "Physics")

    print(f"\n{'═' * 72}")
    print(f"  🔬 Neo4j Query Benchmark — {args.runs} runs each")
    print(f"{'═' * 72}")
    print(f"  Student:    {args.student_id}")
    print(f"  Section:    {args.section_id}")
    print(f"  Subsection: {args.subsection_id}")
    print(f"  Chapter:    {args.chapter_id}")
    print(f"  Concept:    {args.concept_id}")
    print(f"  Grade:      {args.grade} / {args.subject}")
    print(f"  Session:    {args.session_id}")
    print(f"  Profile:    {'ON' if args.profile else 'OFF'}")

    queries = build_queries(
        student_id=args.student_id,
        section_id=args.section_id,
        subsection_id=args.subsection_id,
        chapter_id=args.chapter_id,
        concept_id=args.concept_id,
        session_id=args.session_id,
        grade=args.grade,
        subject=args.subject,
    )

    if args.router:
        queries = [q for q in queries if q.router == args.router]

    print(f"  Queries:    {len(queries)}")

    results = run_benchmark(
        driver,
        queries,
        runs=args.runs,
        do_profile=args.profile,
    )

    print_results(results, do_profile=args.profile)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
