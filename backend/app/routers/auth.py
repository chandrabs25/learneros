"""
Auth router — endpoints for user authentication and profile.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentIdentity, get_authenticated_user
from app.database import write_query
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
        write_query(
            """
            OPTIONAL MATCH (s:Student {id: $student_id})
            DETACH DELETE s
            """,
            student_id=student_id,
        )
        write_query(
            """
            OPTIONAL MATCH (t:Teacher {uid: $uid})
            DETACH DELETE t
            """,
            uid=uid,
        )
        write_query(
            """
            OPTIONAL MATCH (ta:TeacherApplication {applicant_uid: $uid})
            DETACH DELETE ta
            """,
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
