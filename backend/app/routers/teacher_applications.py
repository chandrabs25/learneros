"""
Teacher access application APIs.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from firebase_admin import auth as fb_auth

from app.auth import CurrentAdmin, CurrentUser, get_current_admin, get_current_user
from app.database import read_query, write_query
from app.firebase import get_firebase_app

router = APIRouter(prefix="/api", tags=["teacher-applications"])


class TeacherApplyBody(BaseModel):
    institute_id: str
    department: str | None = Field(default=None, max_length=200)
    statement: str | None = Field(default=None, max_length=2500)
    verification_document_urls: list[str] | None = None


class TeacherApplicationReviewBody(BaseModel):
    note: str | None = Field(default=None, max_length=1200)


def _ensure_active_institute(institute_id: str) -> dict:
    rows = read_query(
        """
        MATCH (i:Institute {id: $institute_id})
        WHERE coalesce(i.is_active, true) = true
        RETURN i.id AS id, i.name AS name
        LIMIT 1
        """,
        institute_id=institute_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Institute not found or inactive")
    return rows[0]


@router.post("/teachers/apply")
async def submit_teacher_application(
    body: TeacherApplyBody,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Submit a teacher access request.
    Any existing pending request by this user is superseded.
    """
    if (user.role or "").lower() in {"teacher", "admin", "superadmin"}:
        raise HTTPException(status_code=400, detail="Your account already has elevated role")

    inst = _ensure_active_institute(body.institute_id)
    app_id = f"teacher_app:{uuid.uuid4().hex}"
    docs = [u for u in (body.verification_document_urls or []) if isinstance(u, str) and u.strip()]

    rows = write_query(
        """
        MATCH (s:Student {id: $student_id})
        MATCH (i:Institute {id: $institute_id})
        OPTIONAL MATCH (s)-[:SUBMITTED_TEACHER_APPLICATION]->(old:TeacherApplication {status: 'PENDING'})
        SET old.status = 'SUPERSEDED',
            old.updated_at = datetime()

        CREATE (a:TeacherApplication {
          id: $app_id,
          applicant_id: $student_id,
          applicant_uid: $uid,
          applicant_email: $email,
          applicant_name: $name,
          institute_id: $institute_id,
          department: $department,
          statement: $statement,
          verification_document_urls: $verification_document_urls,
          status: 'PENDING',
          created_at: datetime(),
          updated_at: datetime()
        })
        CREATE (s)-[:SUBMITTED_TEACHER_APPLICATION]->(a)
        CREATE (a)-[:REQUESTS_INSTITUTE]->(i)
        RETURN a.id AS id, a.status AS status, a.created_at AS created_at
        """,
        student_id=user.student_id,
        uid=user.uid,
        email=user.email or "",
        name=user.name or "",
        institute_id=body.institute_id,
        department=body.department,
        statement=body.statement,
        verification_document_urls=docs,
        app_id=app_id,
    )
    return {
        "status": "ok",
        "application": {
            "id": rows[0]["id"] if rows else app_id,
            "state": rows[0]["status"] if rows else "PENDING",
            "institute_id": inst["id"],
            "institute_name": inst["name"],
        },
    }


@router.get("/teachers/apply/me")
async def my_teacher_application(user: CurrentUser = Depends(get_current_user)):
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:SUBMITTED_TEACHER_APPLICATION]->(a:TeacherApplication)
        OPTIONAL MATCH (a)-[:REQUESTS_INSTITUTE]->(i:Institute)
        OPTIONAL MATCH (a)-[:REVIEWED_BY]->(r:Teacher)
        RETURN a.id AS id,
               a.status AS status,
               a.department AS department,
               a.statement AS statement,
               a.verification_document_urls AS verification_document_urls,
               a.note AS note,
               a.created_at AS created_at,
               a.updated_at AS updated_at,
               i.id AS institute_id,
               i.name AS institute_name,
               r.id AS reviewed_by
        ORDER BY a.created_at DESC
        LIMIT 1
        """,
        student_id=user.student_id,
    )
    return {"application": rows[0] if rows else None}


@router.get("/admin/teacher-applications")
async def admin_list_teacher_applications(
    status: Literal["PENDING", "APPROVED", "REJECTED", "SUPERSEDED"] | None = Query(default="PENDING"),
    _: CurrentAdmin = Depends(get_current_admin),
):
    rows = read_query(
        """
        MATCH (a:TeacherApplication)
        OPTIONAL MATCH (a)-[:REQUESTS_INSTITUTE]->(i:Institute)
        OPTIONAL MATCH (a)-[:REVIEWED_BY]->(r:Teacher)
        WHERE $status IS NULL OR a.status = $status
        RETURN a.id AS id,
               a.status AS status,
               a.applicant_id AS applicant_id,
               a.applicant_uid AS applicant_uid,
               a.applicant_email AS applicant_email,
               a.applicant_name AS applicant_name,
               a.department AS department,
               a.statement AS statement,
               a.verification_document_urls AS verification_document_urls,
               a.note AS note,
               a.created_at AS created_at,
               a.updated_at AS updated_at,
               i.id AS institute_id,
               i.name AS institute_name,
               r.id AS reviewed_by
        ORDER BY a.created_at DESC
        LIMIT 500
        """,
        status=status,
    )
    return rows


@router.post("/admin/teacher-applications/{application_id:path}/approve")
async def admin_approve_teacher_application(
    application_id: str,
    body: TeacherApplicationReviewBody,
    admin: CurrentAdmin = Depends(get_current_admin),
):
    rows = read_query(
        """
        MATCH (a:TeacherApplication {id: $id, status: 'PENDING'})
        RETURN a.applicant_uid AS uid,
               a.institute_id AS institute_id,
               a.applicant_email AS email,
               a.applicant_name AS name
        LIMIT 1
        """,
        id=application_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Pending application not found")
    app = rows[0]
    _ensure_active_institute(app["institute_id"])

    get_firebase_app()
    try:
        user = fb_auth.get_user(app["uid"])
        claims = dict(user.custom_claims or {})
        claims["role"] = "teacher"
        claims["institute_id"] = app["institute_id"]
        fb_auth.set_custom_user_claims(app["uid"], claims)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to set teacher claims")

    write_query(
        """
        MATCH (a:TeacherApplication {id: $id})
        SET a.status = 'APPROVED',
            a.note = $note,
            a.updated_at = datetime()
        WITH a
        MERGE (t:Teacher {id: $teacher_id})
        ON CREATE SET t.uid = $uid,
                      t.email = $email,
                      t.name = $name,
                      t.created_at = datetime()
        SET t.institute_id = $institute_id,
            t.updated_at = datetime()
        WITH a, t
        MATCH (i:Institute {id: $institute_id})
        MERGE (t)-[:BELONGS_TO]->(i)
        MERGE (a)-[:REVIEWED_BY]->(t)
        """,
        id=application_id,
        note=body.note,
        teacher_id=f"teacher:{app['uid']}",
        uid=app["uid"],
        email=app.get("email") or "",
        name=app.get("name") or "",
        institute_id=app["institute_id"],
    )
    return {
        "status": "ok",
        "application_id": application_id,
        "claims": {"role": "teacher", "institute_id": app["institute_id"]},
        "note": "User must refresh token to use teacher routes.",
    }


@router.post("/admin/teacher-applications/{application_id:path}/reject")
async def admin_reject_teacher_application(
    application_id: str,
    body: TeacherApplicationReviewBody,
    admin: CurrentAdmin = Depends(get_current_admin),
):
    rows = write_query(
        """
        MATCH (a:TeacherApplication {id: $id, status: 'PENDING'})
        SET a.status = 'REJECTED',
            a.note = $note,
            a.updated_at = datetime()
        WITH a
        MERGE (r:Teacher {id: $reviewer_id})
        ON CREATE SET r.uid = $reviewer_uid, r.created_at = datetime()
        SET r.updated_at = datetime()
        MERGE (a)-[:REVIEWED_BY]->(r)
        RETURN a.id AS id
        """,
        id=application_id,
        note=body.note,
        reviewer_id=f"teacher:{admin.uid}",
        reviewer_uid=admin.uid,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Pending application not found")
    return {"status": "ok", "application_id": application_id}
