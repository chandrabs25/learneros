"""
Auth router — endpoints for user authentication and profile.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentIdentity, get_authenticated_user
from app.database import async_write_query
from app.firebase import get_firebase_app
from firebase_admin import auth as firebase_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(current_user: CurrentIdentity = Depends(get_authenticated_user)):
    """
    Returns the currently authenticated user's info.
    Used by the frontend to verify auth state and get user details.
    """
    return {
        "uid": current_user.uid,
        "student_id": current_user.student_id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
    }


@router.post("/provision")
async def provision_me(current_user: CurrentIdentity = Depends(get_authenticated_user)):
    """Create a learner graph identity once after Firebase creates the account."""
    if current_user.role not in {"", "student"}:
        return {"status": "ok", "provisioned": False, "role": current_user.role}

    rows = await async_write_query(
        """
        MERGE (s:Student {id: $student_id})
        ON CREATE SET s.name = $name,
                      s.email = $email,
                      s.role = 'student',
                      s.created_at = datetime()
        RETURN s.id AS id
        """,
        _query_name="student.provision",
        student_id=current_user.student_id,
        name=current_user.name or "",
        email=current_user.email or "",
    )
    return {"status": "ok", "provisioned": bool(rows), "role": "student"}


@router.delete("/me")
async def delete_me(current_user: CurrentIdentity = Depends(get_authenticated_user)):
    """
    Permanently delete current user account and linked graph data.
    Deletes:
      - Firebase Auth user
      - Student node + connected data
      - Teacher node (if present)
      - TeacherApplication nodes tied to uid
    """
    uid = current_user.uid
    student_id = current_user.student_id

    # First remove graph data. If this fails, keep Firebase account unchanged.
    try:
        await async_write_query(
            """
            OPTIONAL MATCH (s:Student {id: $student_id})
            DETACH DELETE s
            """,
            _query_name="account.delete_student",
            student_id=student_id,
        )
        await async_write_query(
            """
            OPTIONAL MATCH (t:Teacher {uid: $uid})
            DETACH DELETE t
            """,
            _query_name="account.delete_teacher",
            uid=uid,
        )
        await async_write_query(
            """
            OPTIONAL MATCH (ta:TeacherApplication {applicant_uid: $uid})
            DETACH DELETE ta
            """,
            _query_name="account.delete_teacher_application",
            uid=uid,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete profile data")

    try:
        firebase_auth.delete_user(uid, app=get_firebase_app())
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Profile data deleted but failed to delete Firebase account",
        )

    return {"status": "ok", "deleted": True}
