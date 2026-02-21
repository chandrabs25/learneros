"""
Student Insights API — personalized learning state tracking.

All endpoints require authentication (get_current_user).

Routes:
  GET    /api/students/me/insights                      → Active insights (optional chapter filter)
  GET    /api/students/me/insights/subsection/{subsection_id} → Active insights for a subsection
  GET    /api/students/me/insights/concept/{concept_id} → Full insight log for a concept
  GET    /api/sections/{section_id}/prerequisites-state → Prerequisites + insight states
"""

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, CurrentUser
from app.database import read_query

router = APIRouter(prefix="/api", tags=["insights"])


# ── GET /api/students/me/insights ─────────────────────────────────────────────

@router.get("/students/me/insights")
async def get_my_insights(
    chapter_id: str | None = Query(default=None, description="Filter to insights about this chapter's sections/concepts"),
    user: CurrentUser = Depends(get_current_user),
):
    """
    Returns all active insights for the current student.
    Optionally filtered to a chapter (by matching section and concept ids).
    """
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

            RETURN i.id         AS id,
                   i.type       AS type,
                   i.category   AS category,
                   i.content    AS content,
                   i.created_at AS created_at,
                   [(i)-[:ABOUT_SOURCE]->(src) | src.id][0]  AS source_id,
                   [(i)-[:ABOUT_CONCEPT]->(c)  | c.id][0]   AS concept_id
            ORDER BY i.created_at DESC
            """,
            student_id=user.student_id,
            chapter_id=chapter_id,
        )
    else:
        rows = read_query(
            """
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            RETURN i.id         AS id,
                   i.type       AS type,
                   i.category   AS category,
                   i.content    AS content,
                   i.created_at AS created_at,
                   [(i)-[:ABOUT_SOURCE]->(src) | src.id][0]  AS source_id,
                   [(i)-[:ABOUT_CONCEPT]->(c)  | c.id][0]   AS concept_id
            ORDER BY i.created_at DESC
            """,
            student_id=user.student_id,
        )

    return rows


# ── GET /api/students/me/insights/subsection/{subsection_id} ─────────────────

@router.get("/students/me/insights/subsection/{subsection_id:path}")
async def get_subsection_insights(
    subsection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return active insights linked to a specific subsection for the current student."""
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
    return rows
