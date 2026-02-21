"""
Auth router — endpoints for user authentication and profile.
"""

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
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
