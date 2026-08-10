"""
Institutes API — DB-backed institute listing and student onboarding.

Routes:
  GET    /api/institutes                      -> list active institutes (public)
  PATCH  /api/students/me/institute           -> set student's institute (auth required)
  GET    /api/students/me/institute           -> get student's institute (auth required)
  POST   /api/admin/institutes                -> create institute (admin)
  PATCH  /api/admin/institutes/{institute_id} -> update institute (admin)
  DELETE /api/admin/institutes/{institute_id} -> deactivate institute (admin)
"""

from __future__ import annotations

import re
import uuid
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentAdmin, CurrentUser, get_current_admin, get_current_user
from app.database import async_read_query, async_write_query

router = APIRouter(prefix="/api", tags=["institutes"])
_bootstrap_cache: dict[str, tuple[float, dict]] = {}
_BOOTSTRAP_TTL_SECONDS = 30.0


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return slug or f"inst-{uuid.uuid4().hex[:8]}"


class SetInstituteBody(BaseModel):
    institute_id: str


class StudentProfileUpdateBody(BaseModel):
    institute_id: str | None = None
    grade: int | None = None


class InstituteCreateBody(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1200)
    logo: str | None = Field(default=None, max_length=1200)
    is_active: bool = True


class InstituteUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1200)
    logo: str | None = Field(default=None, max_length=1200)
    is_active: bool | None = None


@router.get("/institutes")
async def list_institutes():
    """Return active institutes from Neo4j. No auth required."""
    return await async_read_query(
        """
        MATCH (i:Institute)
        WHERE coalesce(i.is_active, true) = true
        RETURN i.id AS id,
               i.name AS name,
               i.location AS location,
               i.description AS description,
               i.logo AS logo
        ORDER BY coalesce(i.name, i.id) ASC
        """,
        _query_name="institutes.list",
    )


@router.patch("/students/me/institute")
async def set_student_institute(
    body: SetInstituteBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Set student's institute to a real, active Institute node."""
    exists = await async_read_query(
        """
        MATCH (i:Institute {id: $institute_id})
        WHERE coalesce(i.is_active, true) = true
        RETURN i.id AS id
        LIMIT 1
        """,
        _query_name="student.institute_exists",
        institute_id=body.institute_id,
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Institute not found or inactive")

    rows = await async_write_query(
        """
        MATCH (s:Student {id: $student_id})
        MATCH (i:Institute {id: $institute_id})
        OPTIONAL MATCH (s)-[old:ENROLLED_IN]->(other:Institute)
        WHERE other.id <> $institute_id
        DELETE old
        SET s.institute_id = $institute_id
        MERGE (s)-[:ENROLLED_IN]->(i)
        RETURN s.institute_id AS institute_id
        """,
        _query_name="student.set_institute",
        student_id=user.student_id,
        institute_id=body.institute_id,
    )
    return {"status": "ok", "institute_id": rows[0]["institute_id"] if rows else body.institute_id}


@router.get("/students/me/institute")
async def get_student_institute(
    user: CurrentUser = Depends(get_current_user),
):
    """Return student's currently selected institute details, if set."""
    rows = await async_read_query(
        """
        MATCH (s:Student {id: $student_id})
        OPTIONAL MATCH (s)-[:ENROLLED_IN]->(i:Institute)
        RETURN s.institute_id AS institute_id,
               i.id AS id,
               i.name AS name,
               i.location AS location,
               i.description AS description,
               i.logo AS logo,
               i.is_active AS is_active
        LIMIT 1
        """,
        _query_name="student.get_institute",
        student_id=user.student_id,
    )
    if not rows:
        return {"institute": None}

    row = rows[0]
    institute_id = row.get("institute_id")
    if not institute_id:
        return {"institute": None}

    if row.get("id"):
        return {
            "institute": {
                "id": row.get("id"),
                "name": row.get("name"),
                "location": row.get("location"),
                "description": row.get("description"),
                "logo": row.get("logo"),
                "is_active": row.get("is_active"),
            }
        }

    # Legacy fallback: institute_id exists on Student but no ENROLLED_IN edge yet.
    fallback = await async_read_query(
        """
        MATCH (i:Institute {id: $institute_id})
        RETURN i.id AS id,
               i.name AS name,
               i.location AS location,
               i.description AS description,
               i.logo AS logo,
               i.is_active AS is_active
        LIMIT 1
        """,
        _query_name="student.get_institute_fallback",
        institute_id=institute_id,
    )
    if fallback:
        return {"institute": fallback[0]}
    return {"institute": {"id": institute_id}}


@router.get("/students/me/profile")
async def get_student_profile(
    user: CurrentUser = Depends(get_current_user),
):
    """Return student's profile settings: institute + grade."""
    rows = await async_read_query(
        """
        MATCH (s:Student {id: $student_id})
        OPTIONAL MATCH (s)-[:ENROLLED_IN]->(i:Institute)
        RETURN s.id AS student_id,
               s.name AS name,
               s.email AS email,
               s.grade AS grade,
               s.institute_id AS institute_id,
               i.id AS institute_node_id,
               i.name AS institute_name,
               i.location AS institute_location,
               i.description AS institute_description,
               i.logo AS institute_logo,
               i.is_active AS institute_is_active
        LIMIT 1
        """,
        _query_name="student.profile",
        student_id=user.student_id,
    )
    if not rows:
        return {"student_id": user.student_id, "grade": None, "institute": None}

    r = rows[0]
    institute = None
    if r.get("institute_node_id"):
        institute = {
            "id": r.get("institute_node_id"),
            "name": r.get("institute_name"),
            "location": r.get("institute_location"),
            "description": r.get("institute_description"),
            "logo": r.get("institute_logo"),
            "is_active": r.get("institute_is_active"),
        }
    elif r.get("institute_id"):
        institute = {"id": r.get("institute_id")}

    return {
        "student_id": r.get("student_id"),
        "name": r.get("name"),
        "email": r.get("email"),
        "grade": r.get("grade"),
        "institute": institute,
    }


@router.get("/students/me/dashboard/bootstrap")
async def get_student_dashboard_bootstrap(
    user: CurrentUser = Depends(get_current_user),
):
    """
    One-call bootstrap for student home dashboard.
    Includes profile + available grades to reduce startup round-trips.
    """
    cache_key = user.student_id
    row = _bootstrap_cache.get(cache_key)
    if row:
        ts, payload = row
        if (time.time() - ts) <= _BOOTSTRAP_TTL_SECONDS:
            return payload
        _bootstrap_cache.pop(cache_key, None)

    profile = await get_student_profile(user)
    grades = await async_read_query(
        """
        MATCH (t:Textbook)-[:CONTAINS]->(ch:Chapter)
        WITH t.grade AS grade, t.id AS tid, count(ch) AS ch_count
        WITH grade, sum(ch_count) AS chapter_count, collect(tid)[0] AS textbook_id
        RETURN grade,
               "Class " + toString(grade) AS label,
               chapter_count,
               textbook_id
        ORDER BY grade
        """,
        _query_name="dashboard.grades",
    )
    payload = {
        "student": profile,
        "grades": grades,
    }
    _bootstrap_cache[cache_key] = (time.time(), payload)
    return payload


@router.patch("/students/me/profile")
async def update_student_profile(
    body: StudentProfileUpdateBody,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Update student profile settings.
    - institute_id: set to active institute id OR null to remove institute.
    - grade: set numeric grade OR null to remove grade.
    """
    fields_set = set(body.model_fields_set)
    if not fields_set:
        raise HTTPException(status_code=400, detail="No profile fields provided")

    if "grade" in fields_set and body.grade is not None:
        if body.grade < 1 or body.grade > 12:
            raise HTTPException(status_code=400, detail="grade must be between 1 and 12")

    if "institute_id" in fields_set and body.institute_id:
        exists = await async_read_query(
            """
            MATCH (i:Institute {id: $institute_id})
            WHERE coalesce(i.is_active, true) = true
            RETURN i.id AS id
            LIMIT 1
            """,
            institute_id=body.institute_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Institute not found or inactive")

    if "institute_id" in fields_set:
        if body.institute_id is None:
            await async_write_query(
                """
                MATCH (s:Student {id: $student_id})
                OPTIONAL MATCH (s)-[rel:ENROLLED_IN]->(:Institute)
                DELETE rel
                REMOVE s.institute_id
                """,
                student_id=user.student_id,
            )
        else:
            await async_write_query(
                """
                MATCH (s:Student {id: $student_id})
                MATCH (i:Institute {id: $institute_id})
                OPTIONAL MATCH (s)-[old:ENROLLED_IN]->(other:Institute)
                WHERE other.id <> $institute_id
                DELETE old
                SET s.institute_id = $institute_id
                MERGE (s)-[:ENROLLED_IN]->(i)
                """,
                student_id=user.student_id,
                institute_id=body.institute_id,
            )

    if "grade" in fields_set:
        if body.grade is None:
            await async_write_query(
                """
                MATCH (s:Student {id: $student_id})
                REMOVE s.grade
                """,
                student_id=user.student_id,
            )
        else:
            await async_write_query(
                """
                MATCH (s:Student {id: $student_id})
                SET s.grade = $grade
                """,
                student_id=user.student_id,
                grade=body.grade,
            )

    return await get_student_profile(user)


@router.post("/admin/institutes")
async def admin_create_institute(
    body: InstituteCreateBody,
    _: CurrentAdmin = Depends(get_current_admin),
):
    """Create an institute record (or upsert when same id is reused)."""
    inst_id = body.id or f"institute:{_slugify(body.name)}"
    rows = await async_write_query(
        """
        MERGE (i:Institute {id: $id})
        ON CREATE SET i.created_at = datetime()
        SET i.name = $name,
            i.location = $location,
            i.description = $description,
            i.logo = $logo,
            i.is_active = $is_active,
            i.updated_at = datetime()
        RETURN i.id AS id,
               i.name AS name,
               i.location AS location,
               i.description AS description,
               i.logo AS logo,
               i.is_active AS is_active
        """,
        id=inst_id,
        name=body.name.strip(),
        location=body.location,
        description=body.description,
        logo=body.logo,
        is_active=bool(body.is_active),
    )
    return rows[0]


@router.patch("/admin/institutes/{institute_id:path}")
async def admin_update_institute(
    institute_id: str,
    body: InstituteUpdateBody,
    _: CurrentAdmin = Depends(get_current_admin),
):
    """Update institute metadata."""
    existing = await async_read_query(
        "MATCH (i:Institute {id: $id}) RETURN i.id AS id LIMIT 1",
        id=institute_id,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Institute not found")

    rows = await async_write_query(
        """
        MATCH (i:Institute {id: $id})
        SET i.updated_at = datetime(),
            i.name = coalesce($name, i.name),
            i.location = CASE WHEN $location_set THEN $location ELSE i.location END,
            i.description = CASE WHEN $description_set THEN $description ELSE i.description END,
            i.logo = CASE WHEN $logo_set THEN $logo ELSE i.logo END,
            i.is_active = coalesce($is_active, i.is_active)
        RETURN i.id AS id,
               i.name AS name,
               i.location AS location,
               i.description AS description,
               i.logo AS logo,
               i.is_active AS is_active
        """,
        id=institute_id,
        name=body.name.strip() if body.name else None,
        location=body.location,
        location_set=body.location is not None,
        description=body.description,
        description_set=body.description is not None,
        logo=body.logo,
        logo_set=body.logo is not None,
        is_active=body.is_active,
    )
    return rows[0]


@router.delete("/admin/institutes/{institute_id:path}")
async def admin_delete_institute(
    institute_id: str,
    _: CurrentAdmin = Depends(get_current_admin),
):
    """Soft-delete by marking institute inactive."""
    rows = await async_write_query(
        """
        MATCH (i:Institute {id: $id})
        SET i.is_active = false,
            i.updated_at = datetime()
        RETURN i.id AS id
        """,
        id=institute_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Institute not found")
    return {"status": "ok", "id": institute_id, "is_active": False}
