"""
Admin APIs for user claim management and operational controls.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from firebase_admin import auth as fb_auth

from app.auth import CurrentAdmin, get_current_admin
from app.database import read_query, write_query
from app.firebase import get_firebase_app

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SetUserClaimsBody(BaseModel):
    uid: str | None = None
    email: str | None = None
    role: Literal["student", "teacher", "admin", "superadmin"]
    institute_id: str | None = None


def _resolve_uid(uid: str | None, email: str | None) -> str:
    if uid:
        return uid
    if not email:
        raise HTTPException(status_code=400, detail="Either uid or email is required")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="email must be a valid email address")
    get_firebase_app()
    try:
        user = fb_auth.get_user_by_email(email)
        return user.uid
    except Exception:
        raise HTTPException(status_code=404, detail="User not found for email")


def _ensure_teacher_link(uid: str, institute_id: str) -> None:
    rows = read_query(
        """
        MATCH (i:Institute {id: $institute_id})
        WHERE coalesce(i.is_active, true) = true
        RETURN i.id AS id
        LIMIT 1
        """,
        institute_id=institute_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Institute not found or inactive")

    teacher_id = f"teacher:{uid}"
    write_query(
        """
        MERGE (t:Teacher {id: $teacher_id})
        ON CREATE SET t.uid = $uid,
                      t.created_at = datetime()
        SET t.institute_id = $institute_id,
            t.updated_at = datetime()
        WITH t
        MATCH (i:Institute {id: $institute_id})
        MERGE (t)-[:BELONGS_TO]->(i)
        """,
        teacher_id=teacher_id,
        uid=uid,
        institute_id=institute_id,
    )


@router.post("/users/claims")
async def admin_set_user_claims(
    body: SetUserClaimsBody,
    _: CurrentAdmin = Depends(get_current_admin),
):
    """
    Set Firebase custom claims for a user (teacher/admin/student).
    Teacher role requires institute_id.
    """
    uid = _resolve_uid(body.uid, body.email)
    if body.role == "teacher" and not body.institute_id:
        raise HTTPException(status_code=400, detail="institute_id is required for teacher role")

    get_firebase_app()
    try:
        user = fb_auth.get_user(uid)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found for uid")

    claims = dict(user.custom_claims or {})
    claims["role"] = body.role
    if body.role == "teacher":
        claims["institute_id"] = body.institute_id
        _ensure_teacher_link(uid, body.institute_id or "")
    else:
        claims.pop("institute_id", None)

    try:
        fb_auth.set_custom_user_claims(uid, claims)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to set claims")

    return {
        "status": "ok",
        "uid": uid,
        "claims": claims,
        "note": "User must refresh token (sign out/in or getIdToken(true)) to see updates.",
    }


@router.get("/users/claims")
async def admin_get_user_claims(
    uid: str | None = Query(default=None),
    email: str | None = Query(default=None),
    _: CurrentAdmin = Depends(get_current_admin),
):
    """Lookup current Firebase custom claims for a user."""
    resolved_uid = _resolve_uid(uid, email)
    get_firebase_app()
    try:
        user = fb_auth.get_user(resolved_uid)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "uid": user.uid,
        "email": user.email,
        "display_name": user.display_name,
        "custom_claims": user.custom_claims or {},
    }


# ---------------------------------------------------------------------------
# Rebuild student clusters
# ---------------------------------------------------------------------------

_cluster_status: dict[str, dict] = {}


@router.post("/rebuild-clusters")
async def admin_rebuild_clusters(
    institute_id: str | None = Query(default=None),
    _: CurrentAdmin = Depends(get_current_admin),
):
    """Trigger a cluster rebuild for one or all institutes."""
    import threading

    def _run():
        _cluster_status["state"] = "running"
        _cluster_status["results"] = []
        _cluster_status.pop("error", None)
        try:
            import traceback as tb
            from app.services.clustering_runner import build_for_institute, fetch_institute_ids

            ids = [institute_id] if institute_id else fetch_institute_ids()
            for iid in ids:
                try:
                    result = build_for_institute(
                        iid,
                        k_override=None,
                        min_students=3,
                        min_insights_per_student=3,
                        min_vector_norm=0.001,
                        hdbscan_min_cluster_size=2,
                        hdbscan_min_samples=None,
                    )
                    _cluster_status["results"].append(result)
                except Exception as exc:
                    _cluster_status["results"].append({"institute_id": iid, "status": "error", "error": tb.format_exc()})
            _cluster_status["state"] = "done"
        except Exception as exc:
            import traceback as tb
            _cluster_status["state"] = "error"
            _cluster_status["error"] = tb.format_exc()

    if _cluster_status.get("state") == "running":
        return {"status": "already_running", "message": "A cluster rebuild is already in progress."}

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "message": "Cluster rebuild started in background."}


@router.get("/rebuild-clusters/status")
async def admin_rebuild_clusters_status(
    _: CurrentAdmin = Depends(get_current_admin),
):
    """Check the status of the latest cluster rebuild."""
    return {
        "state": _cluster_status.get("state", "idle"),
        "results": _cluster_status.get("results", []),
        "error": _cluster_status.get("error"),
    }

