"""
Teacher institute analytics dashboard APIs (backend-only).
"""

from __future__ import annotations

import json
import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from openai import OpenAI
from pydantic import BaseModel

from app.auth import CurrentTeacher, get_current_teacher
from app.config import settings
from app.database import read_query
from app.services.teacher_analytics import compute_risk

router = APIRouter(prefix="/api/teachers/me/dashboard", tags=["teacher-dashboard"])

_CACHE_TTL_SECONDS = 20.0
_dashboard_cache: dict[str, tuple[float, dict]] = {}


def _cache_get(key: str) -> dict | None:
    row = _dashboard_cache.get(key)
    if not row:
        return None
    ts, payload = row
    if (time.time() - ts) > _CACHE_TTL_SECONDS:
        _dashboard_cache.pop(key, None)
        return None
    return payload


def _cache_set(key: str, payload: dict) -> None:
    _dashboard_cache[key] = (time.time(), payload)


def _window_days(window: str) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90}
    if window not in mapping:
        raise HTTPException(status_code=400, detail="window must be one of: 7d, 30d, 90d")
    return mapping[window]


def _chapter_scope_ids(chapter_id: str) -> tuple[set[str], set[str]]:
    rows = read_query(
        """
        MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
        OPTIONAL MATCH (sec)-[:CONTAINS]->(ss:Subsection)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(c:Concept)
        RETURN collect(DISTINCT sec.id) + collect(DISTINCT ss.id) AS source_ids,
               collect(DISTINCT c.id) AS concept_ids
        """,
        chapter_id=chapter_id,
    )
    if not rows:
        return set(), set()
    source_ids = {sid for sid in (rows[0].get("source_ids") or []) if sid}
    concept_ids = {cid for cid in (rows[0].get("concept_ids") or []) if cid}
    return source_ids, concept_ids


def _subject_scope_ids(subject: str | None, textbook_grade: int | None) -> tuple[set[str], set[str]]:
    if not subject and textbook_grade is None:
        return set(), set()
    rows = read_query(
        """
        MATCH (sub:Subject)-[:CONTAINS]->(tb:Textbook)
        WHERE ($subject IS NULL OR toLower(sub.name) = toLower($subject))
          AND ($textbook_grade IS NULL OR tb.grade = $textbook_grade)
        MATCH (tb)-[:CONTAINS]->(ch:Chapter)-[:CONTAINS]->(sec:Section)
        OPTIONAL MATCH (sec)-[:CONTAINS]->(ss:Subsection)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(c:Concept)
        RETURN collect(DISTINCT sec.id) + collect(DISTINCT ss.id) AS source_ids,
               collect(DISTINCT c.id) AS concept_ids
        """,
        subject=subject,
        textbook_grade=textbook_grade,
    )
    if not rows:
        return set(), set()
    source_ids = {sid for sid in (rows[0].get("source_ids") or []) if sid}
    concept_ids = {cid for cid in (rows[0].get("concept_ids") or []) if cid}
    return source_ids, concept_ids


def _fetch_institute_students(institute_id: str, grade: int | None = None) -> list[dict]:
    return read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        RETURN s.id AS student_id,
               s.name AS student_name,
               s.email AS student_email,
               s.grade AS student_grade
        ORDER BY coalesce(s.name, s.id) ASC
        """,
        institute_id=institute_id,
        grade=grade,
    )


def _fetch_active_insights_for_students(student_ids: list[str]) -> list[dict]:
    if not student_ids:
        return []
    return read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE s.id IN $student_ids
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH p=(i)-[:SUPERSEDES*1..]->(old:Insight {type: 'MISCONCEPTION'})
        WITH s, i, c, src, max(length(p)) AS max_chain
        RETURN s.id AS student_id,
               i.id AS insight_id,
               i.type AS type,
               i.category AS category,
               i.content AS content,
               i.created_at AS created_at,
               c.id AS concept_id,
               c.name AS concept_name,
               src.id AS source_id,
               src.title AS source_title,
               coalesce(max_chain, 0) AS misconception_history_depth
        ORDER BY i.created_at DESC
        """,
        student_ids=student_ids,
    )


def _insights_filtered(
    insights: list[dict],
    *,
    concept_id: str | None,
    chapter_source_ids: set[str] | None,
    chapter_concept_ids: set[str] | None,
) -> list[dict]:
    out = []
    for ins in insights:
        if concept_id and ins.get("concept_id") != concept_id:
            continue
        if chapter_source_ids is not None or chapter_concept_ids is not None:
            src_ok = chapter_source_ids is not None and ins.get("source_id") in chapter_source_ids
            con_ok = chapter_concept_ids is not None and ins.get("concept_id") in chapter_concept_ids
            if not (src_ok or con_ok):
                continue
        out.append(ins)
    return out


@router.get("/overview")
async def teacher_overview(
    window: Literal["7d", "30d", "90d"] = Query(default="30d"),
    grade: int | None = Query(default=None, ge=1, le=12),
    subject: str | None = Query(default=None),
    textbook_grade: int | None = Query(default=None, ge=1, le=12),
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    cache_key = "|".join(
        [
            "overview",
            teacher.institute_id,
            window,
            str(grade),
            str(subject or ""),
            str(textbook_grade),
        ]
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    days = _window_days(window)
    scope_source_ids: set[str] = set()
    scope_concept_ids: set[str] = set()
    if subject or textbook_grade is not None:
        scope_source_ids, scope_concept_ids = _subject_scope_ids(subject, textbook_grade)
    has_scope = bool(subject or textbook_grade is not None)

    student_count_row = read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        RETURN count(s) AS students
        """,
        institute_id=teacher.institute_id,
        grade=grade,
    )
    student_count = int((student_count_row[0] or {}).get("students") or 0) if student_count_row else 0

    counts_row = read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        WHERE $has_scope = false
           OR src.id IN $scope_source_ids
           OR c.id IN $scope_concept_ids
        RETURN
          sum(CASE WHEN i.type = 'COMPETENCY' THEN 1 ELSE 0 END) AS competency,
          sum(CASE WHEN i.type = 'PARTIAL_UNDERSTANDING' THEN 1 ELSE 0 END) AS partial_understanding,
          sum(CASE WHEN i.type = 'MISCONCEPTION' THEN 1 ELSE 0 END) AS misconception
        """,
        institute_id=teacher.institute_id,
        grade=grade,
        has_scope=has_scope,
        scope_source_ids=list(scope_source_ids),
        scope_concept_ids=list(scope_concept_ids),
    )
    counts_base = counts_row[0] if counts_row else {}
    counts = {
        "COMPETENCY": int(counts_base.get("competency") or 0),
        "PARTIAL_UNDERSTANDING": int(counts_base.get("partial_understanding") or 0),
        "MISCONCEPTION": int(counts_base.get("misconception") or 0),
    }

    category_rows = read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        WHERE $has_scope = false
           OR src.id IN $scope_source_ids
           OR c.id IN $scope_concept_ids
        WITH coalesce(i.category, 'unknown') AS category
        RETURN category, count(*) AS count
        ORDER BY count DESC
        """,
        institute_id=teacher.institute_id,
        grade=grade,
        has_scope=has_scope,
        scope_source_ids=list(scope_source_ids),
        scope_concept_ids=list(scope_concept_ids),
    )
    category_counts: dict[str, int] = {
        str(row.get("category") or "unknown"): int(row.get("count") or 0) for row in category_rows
    }

    high_risk_row = read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH p=(i)-[:SUPERSEDES*1..]->(old:Insight {type: 'MISCONCEPTION'})
        WITH s, i, c, src, coalesce(max(length(p)), 0) AS max_chain
        WHERE i IS NULL
           OR (
             $has_scope = false
             OR src.id IN $scope_source_ids
             OR c.id IN $scope_concept_ids
           )
        WITH s,
             sum(
               CASE
                 WHEN i.type = 'MISCONCEPTION' THEN
                   5.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 WHEN i.type = 'PARTIAL_UNDERSTANDING' THEN
                   2.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 WHEN i.type = 'COMPETENCY' THEN
                   -2.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 ELSE 0.0
               END
             ) AS weighted_score,
             sum(CASE WHEN i.type = 'MISCONCEPTION' AND max_chain >= 2 THEN 1 ELSE 0 END) AS persistent_misconceptions
        WITH (coalesce(weighted_score, 0.0) + (2.0 * coalesce(persistent_misconceptions, 0))) AS risk_score
        RETURN sum(CASE WHEN risk_score >= 15 THEN 1 ELSE 0 END) AS high_risk_students
        """,
        institute_id=teacher.institute_id,
        grade=grade,
        has_scope=has_scope,
        scope_source_ids=list(scope_source_ids),
        scope_concept_ids=list(scope_concept_ids),
    )
    risk_high = int((high_risk_row[0] or {}).get("high_risk_students") or 0) if high_risk_row else 0

    trend_row = read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        WHERE $has_scope = false
           OR src.id IN $scope_source_ids
           OR c.id IN $scope_concept_ids
        WITH datetime() AS now, i
        RETURN
          sum(CASE WHEN i.created_at >= now - duration({days: $days}) THEN 1 ELSE 0 END) AS current_total,
          sum(CASE WHEN i.created_at < now - duration({days: $days})
                    AND i.created_at >= now - duration({days: $days * 2}) THEN 1 ELSE 0 END) AS previous_total,
          sum(CASE WHEN i.type = 'MISCONCEPTION' AND i.created_at >= now - duration({days: $days}) THEN 1 ELSE 0 END) AS current_misconception,
          sum(CASE WHEN i.type = 'MISCONCEPTION' AND i.created_at < now - duration({days: $days})
                    AND i.created_at >= now - duration({days: $days * 2}) THEN 1 ELSE 0 END) AS previous_misconception
        """,
        institute_id=teacher.institute_id,
        grade=grade,
        has_scope=has_scope,
        scope_source_ids=list(scope_source_ids),
        scope_concept_ids=list(scope_concept_ids),
        days=days,
    )
    tr = trend_row[0] if trend_row else {}
    current_total = int(tr.get("current_total") or 0)
    previous_total = int(tr.get("previous_total") or 0)
    current_mis = int(tr.get("current_misconception") or 0)
    previous_mis = int(tr.get("previous_misconception") or 0)

    concept_rows = read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true, type: 'MISCONCEPTION'})
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(scope_c:Concept)
        WHERE (
               $has_scope = false
               OR src.id IN $scope_source_ids
               OR scope_c.id IN $scope_concept_ids
              )
          AND i.created_at >= datetime() - duration({days: $days})
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        RETURN c.id AS concept_id, c.name AS concept_name, count(*) AS count
        ORDER BY count DESC
        LIMIT 8
        """,
        institute_id=teacher.institute_id,
        grade=grade,
        has_scope=has_scope,
        scope_source_ids=list(scope_source_ids),
        scope_concept_ids=list(scope_concept_ids),
        days=days,
    )
    source_rows = read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true, type: 'MISCONCEPTION'})
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(scope_src)
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(scope_c:Concept)
        WHERE (
               $has_scope = false
               OR scope_src.id IN $scope_source_ids
               OR scope_c.id IN $scope_concept_ids
              )
          AND i.created_at >= datetime() - duration({days: $days})
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        RETURN src.id AS source_id, src.title AS source_title, count(*) AS count
        ORDER BY count DESC
        LIMIT 8
        """,
        institute_id=teacher.institute_id,
        grade=grade,
        has_scope=has_scope,
        scope_source_ids=list(scope_source_ids),
        scope_concept_ids=list(scope_concept_ids),
        days=days,
    )

    payload = {
        "institute_id": teacher.institute_id,
        "grade": grade,
        "subject": subject,
        "textbook_grade": textbook_grade,
        "window": window,
        "totals": {
            "students": student_count,
            "competency": counts["COMPETENCY"],
            "partial_understanding": counts["PARTIAL_UNDERSTANDING"],
            "misconception": counts["MISCONCEPTION"],
            "high_risk_students": risk_high,
            "categories": category_counts,
        },
        "trends": {
            "insights": {
                "current": current_total,
                "previous": previous_total,
                "delta": current_total - previous_total,
            },
            "misconception": {
                "current": current_mis,
                "previous": previous_mis,
                "delta": current_mis - previous_mis,
            },
        },
        "top_misconceptions": {
            "concepts": concept_rows,
            "sources": source_rows,
        },
    }
    _cache_set(cache_key, payload)
    return payload


@router.get("/students")
async def teacher_students(
    risk: Literal["LOW", "MEDIUM", "HIGH"] | None = Query(default=None),
    grade: int | None = Query(default=None, ge=1, le=12),
    subject: str | None = Query(default=None),
    textbook_grade: int | None = Query(default=None, ge=1, le=12),
    chapter_id: str | None = Query(default=None),
    concept_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    cache_key = "|".join(
        [
            "students",
            teacher.institute_id,
            str(risk),
            str(grade),
            str(subject or ""),
            str(textbook_grade),
            str(chapter_id or ""),
            str(concept_id or ""),
            str(page),
            str(limit),
        ]
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    chapter_source_ids: set[str] = set()
    chapter_concept_ids: set[str] = set()
    if chapter_id:
        chapter_source_ids, chapter_concept_ids = _chapter_scope_ids(chapter_id)
        if not chapter_source_ids and not chapter_concept_ids:
            return {"page": page, "limit": limit, "total": 0, "items": []}

    subject_source_ids: set[str] = set()
    subject_concept_ids: set[str] = set()
    if subject or textbook_grade is not None:
        subject_source_ids, subject_concept_ids = _subject_scope_ids(subject, textbook_grade)

    if chapter_id and (subject or textbook_grade is not None):
        scope_source_ids = chapter_source_ids & subject_source_ids
        scope_concept_ids = chapter_concept_ids & subject_concept_ids
    elif chapter_id:
        scope_source_ids = chapter_source_ids
        scope_concept_ids = chapter_concept_ids
    elif subject or textbook_grade is not None:
        scope_source_ids = subject_source_ids
        scope_concept_ids = subject_concept_ids
    else:
        scope_source_ids = set()
        scope_concept_ids = set()

    has_scope_filters = bool(chapter_id or subject or textbook_grade is not None)
    has_insight_filters = bool(has_scope_filters or concept_id)
    if has_scope_filters and not scope_source_ids and not scope_concept_ids:
        return {"page": page, "limit": limit, "total": 0, "items": []}

    params = {
        "institute_id": teacher.institute_id,
        "grade": grade,
        "risk": risk,
        "concept_id": concept_id,
        "has_scope_filters": has_scope_filters,
        "scope_source_ids": list(scope_source_ids),
        "scope_concept_ids": list(scope_concept_ids),
        "has_insight_filters": has_insight_filters,
    }

    total_row = read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH p=(i)-[:SUPERSEDES*1..]->(old:Insight {type: 'MISCONCEPTION'})
        WITH s, i, c, src, coalesce(max(length(p)), 0) AS max_chain
        WHERE i IS NULL
           OR (
               ($concept_id IS NULL OR c.id = $concept_id)
               AND (
                 $has_scope_filters = false
                 OR src.id IN $scope_source_ids
                 OR c.id IN $scope_concept_ids
               )
           )
        WITH s,
             count(i) AS matched_insight_count,
             sum(CASE WHEN i.type = 'COMPETENCY' THEN 1 ELSE 0 END) AS competency_count,
             sum(CASE WHEN i.type = 'PARTIAL_UNDERSTANDING' THEN 1 ELSE 0 END) AS partial_count,
             sum(CASE WHEN i.type = 'MISCONCEPTION' THEN 1 ELSE 0 END) AS misconception_count,
             sum(
               CASE
                 WHEN i.type = 'MISCONCEPTION' THEN
                   5.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 WHEN i.type = 'PARTIAL_UNDERSTANDING' THEN
                   2.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 WHEN i.type = 'COMPETENCY' THEN
                   -2.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 ELSE 0.0
               END
             ) AS weighted_score,
             sum(CASE WHEN i.type = 'MISCONCEPTION' AND max_chain >= 2 THEN 1 ELSE 0 END) AS persistent_misconceptions
        WITH s,
             matched_insight_count,
             competency_count,
             partial_count,
             misconception_count,
             (coalesce(weighted_score, 0.0) + (2.0 * coalesce(persistent_misconceptions, 0))) AS risk_score,
             persistent_misconceptions
        WHERE ($has_insight_filters = false OR matched_insight_count > 0)
          AND (
            $risk IS NULL OR
            ($risk = 'HIGH' AND risk_score >= 15) OR
            ($risk = 'MEDIUM' AND risk_score >= 7 AND risk_score < 15) OR
            ($risk = 'LOW' AND risk_score < 7)
          )
        RETURN count(s) AS total
        """,
        **params,
    )
    total = int((total_row[0] or {}).get("total") or 0) if total_row else 0

    paged_rows = read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id = $institute_id
          AND ($grade IS NULL OR s.grade = $grade)
          AND coalesce(s.role, 'student') = 'student'
        OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH p=(i)-[:SUPERSEDES*1..]->(old:Insight {type: 'MISCONCEPTION'})
        WITH s, i, c, src, coalesce(max(length(p)), 0) AS max_chain
        WHERE i IS NULL
           OR (
               ($concept_id IS NULL OR c.id = $concept_id)
               AND (
                 $has_scope_filters = false
                 OR src.id IN $scope_source_ids
                 OR c.id IN $scope_concept_ids
               )
           )
        WITH s,
             max(i.created_at) AS last_activity,
             count(i) AS matched_insight_count,
             sum(CASE WHEN i.type = 'COMPETENCY' THEN 1 ELSE 0 END) AS competency_count,
             sum(CASE WHEN i.type = 'PARTIAL_UNDERSTANDING' THEN 1 ELSE 0 END) AS partial_count,
             sum(CASE WHEN i.type = 'MISCONCEPTION' THEN 1 ELSE 0 END) AS misconception_count,
             sum(
               CASE
                 WHEN i.type = 'MISCONCEPTION' THEN
                   5.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 WHEN i.type = 'PARTIAL_UNDERSTANDING' THEN
                   2.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 WHEN i.type = 'COMPETENCY' THEN
                   -2.0 * (
                     CASE
                       WHEN i.created_at >= datetime() - duration({days: 7}) THEN 1.25
                       WHEN i.created_at >= datetime() - duration({days: 30}) THEN 1.0
                       ELSE 0.75
                     END
                   )
                 ELSE 0.0
               END
             ) AS weighted_score,
             sum(CASE WHEN i.type = 'MISCONCEPTION' AND max_chain >= 2 THEN 1 ELSE 0 END) AS persistent_misconceptions
        WITH s,
             last_activity,
             matched_insight_count,
             competency_count,
             partial_count,
             misconception_count,
             (coalesce(weighted_score, 0.0) + (2.0 * coalesce(persistent_misconceptions, 0))) AS risk_score,
             persistent_misconceptions
        WHERE ($has_insight_filters = false OR matched_insight_count > 0)
          AND (
            $risk IS NULL OR
            ($risk = 'HIGH' AND risk_score >= 15) OR
            ($risk = 'MEDIUM' AND risk_score >= 7 AND risk_score < 15) OR
            ($risk = 'LOW' AND risk_score < 7)
          )
        WITH s, last_activity, matched_insight_count, competency_count, partial_count, misconception_count, risk_score, persistent_misconceptions,
             CASE
               WHEN risk_score >= 15 THEN 'HIGH'
               WHEN risk_score >= 7 THEN 'MEDIUM'
               ELSE 'LOW'
             END AS risk_band
        ORDER BY risk_score DESC, coalesce(s.name, s.id) ASC
        SKIP $skip
        LIMIT $limit
        RETURN s.id AS student_id,
               s.name AS student_name,
               s.email AS student_email,
               s.grade AS student_grade,
               risk_score,
               risk_band,
               competency_count,
               partial_count,
               misconception_count,
               persistent_misconceptions,
               last_activity
        """,
        **params,
        skip=(page - 1) * limit,
        limit=limit,
    )

    items: list[dict] = []
    for row in paged_rows:
        misconception_count = int(row.get("misconception_count") or 0)
        competency_count = int(row.get("competency_count") or 0)
        persistent = int(row.get("persistent_misconceptions") or 0)
        reasons: list[str] = []
        if misconception_count >= 3:
            reasons.append("HIGH_MISCONCEPTION_COUNT")
        if persistent > 0:
            reasons.append("PERSISTENT_MISCONCEPTIONS")
        if competency_count == 0 and misconception_count > 0:
            reasons.append("LOW_COMPETENCY_OFFSET")

        items.append(
            {
                "student_id": row.get("student_id"),
                "name": row.get("student_name") or row.get("student_id"),
                "email": row.get("student_email"),
                "grade": row.get("student_grade"),
                "risk_score": round(float(row.get("risk_score") or 0.0), 2),
                "risk_band": row.get("risk_band"),
                "reasons": reasons,
                "active_counts": {
                    "competency": competency_count,
                    "partial_understanding": int(row.get("partial_count") or 0),
                    "misconception": misconception_count,
                },
                "last_activity": str(row.get("last_activity")) if row.get("last_activity") else None,
            }
        )

    payload = {
        "page": page,
        "limit": limit,
        "total": total,
        "items": items,
    }
    _cache_set(cache_key, payload)
    return payload


@router.get("/students/{student_id:path}")
async def teacher_student_detail(
    student_id: str,
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    student_rows = read_query(
        """
        MATCH (s:Student {id: $student_id})
        WHERE coalesce(s.role, 'student') = 'student'
        RETURN s.id AS student_id,
               s.name AS student_name,
               s.email AS student_email,
               s.institute_id AS institute_id
        LIMIT 1
        """,
        student_id=student_id,
    )
    if not student_rows:
        raise HTTPException(status_code=404, detail="Student not found")
    student = student_rows[0]
    if student.get("institute_id") != teacher.institute_id:
        raise HTTPException(status_code=403, detail="Student is outside your institute")

    insights = _fetch_active_insights_for_students([student_id])
    risk_info = compute_risk(insights)

    active_counts = {"COMPETENCY": 0, "PARTIAL_UNDERSTANDING": 0, "MISCONCEPTION": 0}
    for ins in insights:
        itype = str(ins.get("type") or "")
        if itype in active_counts:
            active_counts[itype] += 1

    timeline_rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:SUPERSEDES]->(old:Insight)
        WITH i, src, c, collect(DISTINCT old.id) AS supersedes_ids
        RETURN i.id AS id,
               i.type AS type,
               i.category AS category,
               i.content AS content,
               i.is_active AS is_active,
               i.created_at AS created_at,
               c.id AS concept_id,
               c.name AS concept_name,
               src.id AS source_id,
               src.title AS source_title,
               supersedes_ids
        ORDER BY i.created_at DESC
        LIMIT 120
        """,
        student_id=student_id,
    )

    return {
        "student": {
            "student_id": student["student_id"],
            "name": student.get("student_name"),
            "email": student.get("student_email"),
            "institute_id": student.get("institute_id"),
        },
        "risk": risk_info,
        "active_counts": {
            "competency": active_counts["COMPETENCY"],
            "partial_understanding": active_counts["PARTIAL_UNDERSTANDING"],
            "misconception": active_counts["MISCONCEPTION"],
        },
        "active_insights": [
            {
                **ins,
                "created_at": str(ins.get("created_at")) if ins.get("created_at") else None,
            }
            for ins in insights
        ],
        "timeline": [
            {
                **row,
                "created_at": str(row.get("created_at")) if row.get("created_at") else None,
            }
            for row in timeline_rows
        ],
    }


def _resolve_snapshot(institute_id: str, snapshot: str) -> dict | None:
    if snapshot == "latest":
        rows = read_query(
            """
            MATCH (snap:StudentClusterSnapshot {institute_id: $institute_id})
            RETURN snap.id AS id,
                   snap.institute_id AS institute_id,
                   snap.run_at AS run_at,
                   snap.algorithm AS algorithm,
                   snap.k AS k,
                   snap.student_count AS student_count,
                   snap.eligible_students AS eligible_students,
                   snap.noise_students AS noise_students,
                   snap.quality_json AS quality_json,
                   snap.engine_version AS engine_version
            ORDER BY snap.run_at DESC
            LIMIT 1
            """,
            institute_id=institute_id,
        )
    else:
        rows = read_query(
            """
            MATCH (snap:StudentClusterSnapshot {id: $snapshot_id, institute_id: $institute_id})
            RETURN snap.id AS id,
                   snap.institute_id AS institute_id,
                   snap.run_at AS run_at,
                   snap.algorithm AS algorithm,
                   snap.k AS k,
                   snap.student_count AS student_count,
                   snap.eligible_students AS eligible_students,
                   snap.noise_students AS noise_students,
                   snap.quality_json AS quality_json,
                   snap.engine_version AS engine_version
            LIMIT 1
            """,
            snapshot_id=snapshot,
            institute_id=institute_id,
        )
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Cluster trends — temporal analysis
# ---------------------------------------------------------------------------

@router.get("/cluster-trends")
async def cluster_trends(
    window: str = Query(default="30d"),
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    cache_key = "|".join(["cluster_trends", teacher.institute_id, window])
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    days = _window_days(window)
    # Fetch all snapshots within the window, ordered by time
    snapshot_rows = read_query(
        """
        MATCH (snap:StudentClusterSnapshot {institute_id: $institute_id})
        WHERE snap.run_at >= datetime() - duration({days: $days})
        OPTIONAL MATCH (c:StudentCluster {snapshot_id: snap.id, institute_id: $institute_id})
        WITH snap, count(c) AS cluster_count
        RETURN snap.id AS snapshot_id,
               toString(snap.run_at) AS run_at,
               snap.algorithm AS algorithm,
               snap.student_count AS student_count,
               snap.noise_students AS noise_students,
               snap.k AS k,
               snap.quality_json AS quality_json,
               snap.high_risk_count AS high_risk_count,
               snap.medium_risk_count AS medium_risk_count,
               snap.low_risk_count AS low_risk_count,
               cluster_count
        ORDER BY snap.run_at ASC
        """,
        institute_id=teacher.institute_id,
        days=days,
    )

    snapshots = []
    for r in snapshot_rows:
        silhouette = 0.0
        try:
            q = json.loads(r.get("quality_json") or "{}")
            silhouette = float(q.get("silhouette", 0.0))
        except Exception:
            pass
        snapshots.append({
            "snapshot_id": r.get("snapshot_id"),
            "run_at": r.get("run_at"),
            "algorithm": r.get("algorithm"),
            "student_count": int(r.get("student_count") or 0),
            "noise_students": int(r.get("noise_students") or 0),
            "cluster_count": int(r.get("cluster_count") or 0),
            "k": int(r.get("k") or 0),
            "silhouette": silhouette,
            "high_risk_count": int(r.get("high_risk_count") or 0),
            "medium_risk_count": int(r.get("medium_risk_count") or 0),
            "low_risk_count": int(r.get("low_risk_count") or 0),
        })

    # Compute migrations between consecutive snapshot pairs
    migrations: list[dict] = []
    students_improved = 0
    students_declined = 0
    students_stable = 0

    if len(snapshots) >= 2:
        prev_snap = snapshots[-2]
        curr_snap = snapshots[-1]
        prev_id = prev_snap["snapshot_id"]
        curr_id = curr_snap["snapshot_id"]

        migration_rows = read_query(
            """
            MATCH (s:Student)-[:IN_CLUSTER {snapshot_id: $prev_id}]->(old:StudentCluster)
            MATCH (s)-[:IN_CLUSTER {snapshot_id: $curr_id}]->(new:StudentCluster)
            WHERE s.institute_id = $institute_id
            RETURN s.id AS student_id,
                   s.name AS student_name,
                   old.id AS from_cluster_id,
                   old.label AS from_cluster_label,
                   old.avg_risk AS from_avg_risk,
                   new.id AS to_cluster_id,
                   new.label AS to_cluster_label,
                   new.avg_risk AS to_avg_risk
            """,
            prev_id=prev_id,
            curr_id=curr_id,
            institute_id=teacher.institute_id,
        )

        for m in migration_rows:
            from_risk = float(m.get("from_avg_risk") or 0)
            to_risk = float(m.get("to_avg_risk") or 0)
            from_cid = m.get("from_cluster_id")
            to_cid = m.get("to_cluster_id")

            if from_cid == to_cid:
                students_stable += 1
                continue

            if to_risk < from_risk:
                direction = "improved"
                students_improved += 1
            elif to_risk > from_risk:
                direction = "declined"
                students_declined += 1
            else:
                direction = "lateral"
                students_stable += 1

            migrations.append({
                "student_id": m.get("student_id"),
                "student_name": m.get("student_name") or m.get("student_id"),
                "from_cluster_label": m.get("from_cluster_label"),
                "to_cluster_label": m.get("to_cluster_label"),
                "direction": direction,
            })

    payload = {
        "snapshots": snapshots,
        "migrations": migrations[:20],
        "summary": {
            "total_snapshots": len(snapshots),
            "students_improved": students_improved,
            "students_declined": students_declined,
            "students_stable": students_stable,
        },
    }
    _cache_set(cache_key, payload)
    return payload


@router.get("/clusters")
async def teacher_clusters(
    snapshot: str = Query(default="latest"),
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    cache_key = "|".join(["clusters", teacher.institute_id, snapshot])
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    snap = _resolve_snapshot(teacher.institute_id, snapshot)
    if not snap:
        payload = {"snapshot_id": None, "run_at": None, "clusters": []}
        _cache_set(cache_key, payload)
        return payload

    rows = read_query(
        """
        MATCH (c:StudentCluster {snapshot_id: $snapshot_id, institute_id: $institute_id})
        RETURN c.id AS cluster_id,
               c.label AS label,
               c.size AS size,
               c.avg_risk AS avg_risk,
               c.is_noise_cluster AS is_noise_cluster,
               c.top_concepts_json AS top_concepts_json,
               c.top_terms_json AS top_terms_json,
               c.risk_band_counts_json AS risk_band_counts_json,
               c.top_misconceptions_json AS top_misconceptions_json
        ORDER BY c.size DESC, c.id ASC
        """,
        snapshot_id=snap["id"],
        institute_id=teacher.institute_id,
    )

    clusters = []
    for r in rows:
        try:
            top_concepts = json.loads(r.get("top_concepts_json") or "[]")
        except Exception:
            top_concepts = []
        try:
            top_terms = json.loads(r.get("top_terms_json") or "[]")
        except Exception:
            top_terms = []
        try:
            risk_band_counts = json.loads(r.get("risk_band_counts_json") or "{}")
        except Exception:
            risk_band_counts = {}
        try:
            top_misconceptions = json.loads(r.get("top_misconceptions_json") or "[]")
        except Exception:
            top_misconceptions = []
        clusters.append(
            {
                "cluster_id": r.get("cluster_id"),
                "label": r.get("label"),
                "size": int(r.get("size") or 0),
                "avg_risk": float(r.get("avg_risk") or 0.0),
                "is_noise_cluster": bool(r.get("is_noise_cluster") or False),
                "top_concepts": top_concepts,
                "top_terms": top_terms,
                "risk_band_counts": risk_band_counts,
                "top_misconceptions": top_misconceptions,
            }
        )

    try:
        quality = json.loads(snap.get("quality_json") or "{}")
    except Exception:
        quality = {}
    if not isinstance(quality, dict):
        quality = {}
    if "noise_ratio" not in quality:
        noise_students = int(snap.get("noise_students") or 0)
        student_count = int(snap.get("student_count") or 0)
        quality["noise_ratio"] = round(noise_students / max(1, student_count), 4)
    if "silhouette" not in quality:
        quality["silhouette"] = 0.0
    if "size_imbalance" not in quality:
        quality["size_imbalance"] = 0.0

    payload = {
        "snapshot_id": snap["id"],
        "run_at": str(snap.get("run_at")) if snap.get("run_at") else None,
        "algorithm": snap.get("algorithm"),
        "engine_version": snap.get("engine_version") or "v1",
        "k": snap.get("k"),
        "student_count": snap.get("student_count"),
        "eligible_students": snap.get("eligible_students"),
        "noise_students": snap.get("noise_students"),
        "quality": quality,
        "clusters": clusters,
    }
    _cache_set(cache_key, payload)
    return payload


@router.get("/clusters/{cluster_id:path}")
async def teacher_cluster_detail(
    cluster_id: str,
    snapshot: str = Query(default="latest"),
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    cache_key = "|".join(["cluster_detail", teacher.institute_id, snapshot, cluster_id])
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    snap = _resolve_snapshot(teacher.institute_id, snapshot)
    if not snap:
        raise HTTPException(status_code=404, detail="No cluster snapshot found")

    cluster_rows = read_query(
        """
        MATCH (c:StudentCluster {id: $cluster_id, snapshot_id: $snapshot_id, institute_id: $institute_id})
        RETURN c.id AS cluster_id,
               c.label AS label,
               c.size AS size,
               c.avg_risk AS avg_risk,
               c.is_noise_cluster AS is_noise_cluster,
               c.top_concepts_json AS top_concepts_json,
               c.top_terms_json AS top_terms_json,
               c.risk_band_counts_json AS risk_band_counts_json,
               c.top_misconceptions_json AS top_misconceptions_json,
               c.recommended_actions_json AS recommended_actions_json
        LIMIT 1
        """,
        cluster_id=cluster_id,
        snapshot_id=snap["id"],
        institute_id=teacher.institute_id,
    )
    if not cluster_rows:
        raise HTTPException(status_code=404, detail="Cluster not found")
    c = cluster_rows[0]

    member_rows = read_query(
        """
        MATCH (s:Student)-[r:IN_CLUSTER {snapshot_id: $snapshot_id}]->(c:StudentCluster {id: $cluster_id})
        WHERE s.institute_id = $institute_id
        RETURN s.id AS student_id,
               s.name AS student_name,
               s.email AS student_email,
               r.confidence AS cluster_confidence,
               r.distance AS cluster_distance
        ORDER BY coalesce(s.name, s.id) ASC
        """,
        snapshot_id=snap["id"],
        cluster_id=cluster_id,
        institute_id=teacher.institute_id,
    )

    member_ids = [m["student_id"] for m in member_rows]
    member_insights = _fetch_active_insights_for_students(member_ids)
    by_student: dict[str, list[dict]] = {sid: [] for sid in member_ids}
    for ins in member_insights:
        by_student.setdefault(ins["student_id"], []).append(ins)

    members = []
    for m in member_rows:
        risk = compute_risk(by_student.get(m["student_id"], []))
        members.append(
            {
                "student_id": m["student_id"],
                "name": m.get("student_name") or m["student_id"],
                "email": m.get("student_email"),
                "risk_score": risk["risk_score"],
                "risk_band": risk["risk_band"],
                "reasons": risk["reasons"],
                "cluster_confidence": m.get("cluster_confidence"),
                "cluster_distance": m.get("cluster_distance"),
            }
        )
    members.sort(key=lambda x: (-x["risk_score"], x["name"]))

    try:
        top_concepts = json.loads(c.get("top_concepts_json") or "[]")
    except Exception:
        top_concepts = []
    try:
        top_terms = json.loads(c.get("top_terms_json") or "[]")
    except Exception:
        top_terms = []
    try:
        risk_band_counts = json.loads(c.get("risk_band_counts_json") or "{}")
    except Exception:
        risk_band_counts = {}
    try:
        top_misconceptions = json.loads(c.get("top_misconceptions_json") or "[]")
    except Exception:
        top_misconceptions = []
    try:
        recommended_actions = json.loads(c.get("recommended_actions_json") or "[]")
    except Exception:
        recommended_actions = []

    member_count_by_risk_band = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for m in members:
        band = str(m.get("risk_band") or "LOW")
        if band not in member_count_by_risk_band:
            member_count_by_risk_band[band] = 0
        member_count_by_risk_band[band] += 1

    representative_insights: list[dict] = []
    for ins in member_insights:
        itype = str(ins.get("type") or "").upper()
        if itype not in {"MISCONCEPTION", "PARTIAL_UNDERSTANDING"}:
            continue
        representative_insights.append(
            {
                "insight_id": ins.get("insight_id"),
                "student_id": ins.get("student_id"),
                "type": itype,
                "content": ins.get("content"),
                "concept_id": ins.get("concept_id"),
                "concept_name": ins.get("concept_name"),
                "source_id": ins.get("source_id"),
                "source_title": ins.get("source_title"),
                "created_at": str(ins.get("created_at")) if ins.get("created_at") else None,
            }
        )
    representative_insights = representative_insights[:12]

    payload = {
        "snapshot_id": snap["id"],
        "run_at": str(snap.get("run_at")) if snap.get("run_at") else None,
        "algorithm": snap.get("algorithm"),
        "engine_version": snap.get("engine_version") or "v1",
        "cluster": {
            "cluster_id": c.get("cluster_id"),
            "label": c.get("label"),
            "size": int(c.get("size") or 0),
            "avg_risk": float(c.get("avg_risk") or 0.0),
            "is_noise_cluster": bool(c.get("is_noise_cluster") or False),
            "top_concepts": top_concepts,
            "top_terms": top_terms,
            "risk_band_counts": risk_band_counts,
            "top_misconceptions": top_misconceptions,
        },
        "member_count_by_risk_band": member_count_by_risk_band,
        "representative_insights": representative_insights,
        "recommended_actions": recommended_actions,
        "members": members,
    }
    _cache_set(cache_key, payload)
    return payload


# ---------------------------------------------------------------------------
# LLM-powered cluster suggestions
# ---------------------------------------------------------------------------

_llm_client: OpenAI | None = None
_suggestion_rate: dict[str, list[float]] = {}


def _get_llm_client() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        if not settings.FIREWORKS_API_KEY:
            raise HTTPException(status_code=500, detail="FIREWORKS_API_KEY not configured")
        _llm_client = OpenAI(api_key=settings.FIREWORKS_API_KEY, base_url=settings.FIREWORKS_BASE_URL)
    return _llm_client


def _check_suggestion_rate(teacher_id: str, limit: int = 10, window: int = 60) -> None:
    now = time.time()
    timestamps = _suggestion_rate.get(teacher_id, [])
    timestamps = [t for t in timestamps if now - t < window]
    if len(timestamps) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded — try again in a minute")
    timestamps.append(now)
    _suggestion_rate[teacher_id] = timestamps


class SuggestionFilters(BaseModel):
    risk_bands: list[str] | None = None
    insight_types: list[str] | None = None
    concept_ids: list[str] | None = None
    max_insights: int = 15


class GenerateSuggestionsPayload(BaseModel):
    teacher_context: str = ""
    filters: SuggestionFilters = SuggestionFilters()


@router.post("/clusters/{cluster_id:path}/generate-suggestions")
async def generate_cluster_suggestions(
    cluster_id: str,
    body: GenerateSuggestionsPayload,
    request: Request,
    snapshot: str = Query(default="latest"),
    teacher: CurrentTeacher = Depends(get_current_teacher),
):
    _check_suggestion_rate(teacher.institute_id)

    snap = _resolve_snapshot(teacher.institute_id, snapshot)
    if not snap:
        raise HTTPException(status_code=404, detail="No cluster snapshot found")

    # Fetch cluster metadata
    cluster_rows = read_query(
        """
        MATCH (c:StudentCluster {id: $cluster_id, snapshot_id: $snapshot_id, institute_id: $institute_id})
        RETURN c.id AS cluster_id,
               c.label AS label,
               c.size AS size,
               c.avg_risk AS avg_risk,
               c.top_concepts_json AS top_concepts_json,
               c.risk_band_counts_json AS risk_band_counts_json,
               c.top_misconceptions_json AS top_misconceptions_json
        LIMIT 1
        """,
        cluster_id=cluster_id,
        snapshot_id=snap["id"],
        institute_id=teacher.institute_id,
    )
    if not cluster_rows:
        raise HTTPException(status_code=404, detail="Cluster not found")
    c = cluster_rows[0]

    # Fetch members + their insights
    member_rows = read_query(
        """
        MATCH (s:Student)-[r:IN_CLUSTER {snapshot_id: $snapshot_id}]->(cl:StudentCluster {id: $cluster_id})
        WHERE s.institute_id = $institute_id
        RETURN s.id AS student_id, s.name AS student_name
        """,
        snapshot_id=snap["id"],
        cluster_id=cluster_id,
        institute_id=teacher.institute_id,
    )
    member_ids = [m["student_id"] for m in member_rows]
    all_insights = _fetch_active_insights_for_students(member_ids)

    # Compute per-student risk bands for filtering
    by_student: dict[str, list[dict]] = {sid: [] for sid in member_ids}
    for ins in all_insights:
        by_student.setdefault(ins["student_id"], []).append(ins)

    student_risk_bands: dict[str, str] = {}
    for sid in member_ids:
        risk = compute_risk(by_student.get(sid, []))
        student_risk_bands[sid] = str(risk.get("risk_band", "LOW"))

    # Apply filters
    filters = body.filters
    filtered_insights: list[dict] = []
    for ins in all_insights:
        itype = str(ins.get("type") or "").upper()
        sid = ins.get("student_id", "")

        if filters.risk_bands:
            if student_risk_bands.get(sid, "LOW") not in [rb.upper() for rb in filters.risk_bands]:
                continue
        if filters.insight_types:
            if itype not in [it.upper() for it in filters.insight_types]:
                continue
        if filters.concept_ids:
            if ins.get("concept_id") not in filters.concept_ids:
                continue

        filtered_insights.append(ins)

    filtered_insights = filtered_insights[: filters.max_insights]

    # Parse cluster metadata
    try:
        top_concepts = json.loads(c.get("top_concepts_json") or "[]")
    except Exception:
        top_concepts = []
    try:
        risk_band_counts = json.loads(c.get("risk_band_counts_json") or "{}")
    except Exception:
        risk_band_counts = {}
    try:
        top_misconceptions = json.loads(c.get("top_misconceptions_json") or "[]")
    except Exception:
        top_misconceptions = []

    concept_names = [str(tc.get("name") or tc.get("id", "")) for tc in top_concepts[:5]]
    misconception_lines = []
    for m in top_misconceptions[:8]:
        stmt = m.get("statement") or m.get("content") or "unknown"
        concept = m.get("concept") or m.get("concept_name") or ""
        count = m.get("count", 1)
        misconception_lines.append(f"- \"{stmt}\" (concept: {concept}, count: {count})")

    insight_lines = []
    for ins in filtered_insights:
        student_name = ""
        for mr in member_rows:
            if mr["student_id"] == ins.get("student_id"):
                student_name = mr.get("student_name") or ins.get("student_id", "")
                break
        concept = ins.get("concept_name") or ins.get("concept_id") or "general"
        source = ins.get("source_title") or ins.get("source_id") or ""
        content = ins.get("content") or ""
        itype = ins.get("type", "")
        insight_lines.append(
            f"- [{itype}] Student: {student_name}, Concept: {concept}, "
            f"Source: {source}, Detail: {content}"
        )

    high = risk_band_counts.get("HIGH", 0)
    medium = risk_band_counts.get("MEDIUM", 0)
    low = risk_band_counts.get("LOW", 0)

    system_prompt = (
        "You are an expert teaching assistant analyzing student cluster data for a teacher. "
        "Generate 3-5 specific, actionable teaching suggestions based on the cluster data below. "
        "Each suggestion should:\n"
        "1. Reference specific concepts or misconceptions from the data\n"
        "2. Suggest a concrete classroom activity or intervention\n"
        "3. Be prioritized by urgency (high-risk patterns first)\n"
        "4. Be practical and immediately usable\n\n"
        "Return ONLY a JSON array of suggestion strings, no other text. Example:\n"
        '[\"suggestion 1\", \"suggestion 2\", \"suggestion 3\"]'
    )

    user_prompt = (
        f"CLUSTER SUMMARY:\n"
        f"- Students in cluster: {len(member_ids)}\n"
        f"- Top concepts: {', '.join(concept_names) if concept_names else 'none identified'}\n"
        f"- Risk distribution: {high} high, {medium} medium, {low} low risk\n\n"
        f"TOP MISCONCEPTIONS IN CLUSTER:\n"
        f"{chr(10).join(misconception_lines) if misconception_lines else '(none)'}\n\n"
        f"FILTERED STUDENT INSIGHTS ({len(insight_lines)} insights):\n"
        f"{chr(10).join(insight_lines) if insight_lines else '(none)'}\n\n"
    )

    if body.teacher_context.strip():
        user_prompt += f"TEACHER'S CONTEXT:\n{body.teacher_context.strip()}\n\n"

    filters_desc = []
    if filters.risk_bands:
        filters_desc.append(f"risk_bands={filters.risk_bands}")
    if filters.insight_types:
        filters_desc.append(f"types={filters.insight_types}")
    if filters.concept_ids:
        filters_desc.append(f"concepts={filters.concept_ids}")
    if filters_desc:
        user_prompt += f"ACTIVE FILTERS: {', '.join(filters_desc)}\n\n"

    user_prompt += "Generate your teaching suggestions now."

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.FIREWORKS_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        timeout=60,
    )
    raw = resp.choices[0].message.content or "[]"
    if isinstance(raw, list):
        raw = "".join(
            p.get("text", "") for p in raw if isinstance(p, dict) and p.get("type") == "text"
        )
    raw = str(raw).strip()

    # Parse the JSON array from the LLM response
    suggestions: list[str] = []
    try:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            suggestions = [str(s) for s in parsed[:5]]
        else:
            suggestions = [str(raw)]
    except json.JSONDecodeError:
        suggestions = [line.lstrip("- ").strip() for line in raw.split("\n") if line.strip()]
        suggestions = suggestions[:5]

    return {
        "suggestions": suggestions,
        "model": settings.FIREWORKS_MODEL,
        "insights_used": len(filtered_insights),
        "filters_applied": {
            "risk_bands": filters.risk_bands,
            "insight_types": filters.insight_types,
            "concept_ids": filters.concept_ids,
            "max_insights": filters.max_insights,
        },
    }
