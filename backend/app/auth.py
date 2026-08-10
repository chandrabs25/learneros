"""
Auth middleware — extracts and verifies Firebase ID tokens from requests.

Two dependency functions:
  - get_current_user:   REQUIRED auth — 401 if no token (for insights, progress)
  - get_optional_user:  OPTIONAL auth — returns None if no token (for teaching)
"""

import logging

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.firebase import verify_id_token

# Extracts "Bearer <token>" from Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


class CurrentUser:
    """Authenticated user info attached to each request."""

    def __init__(self, uid: str, email: str | None, name: str | None, role: str):
        self.uid = uid
        self.student_id = f"student:{uid}"
        self.email = email
        self.name = name
        self.role = role

    def __repr__(self):
        return f"CurrentUser(uid={self.uid}, email={self.email}, role={self.role})"


class CurrentIdentity:
    """Authenticated identity independent of learner/teacher/admin domain models."""

    def __init__(self, uid: str, email: str | None, name: str | None, role: str):
        self.uid = uid
        self.email = email
        self.name = name
        self.role = role
        self.student_id = f"student:{uid}"
        self.teacher_id = f"teacher:{uid}"

    def __repr__(self):
        return f"CurrentIdentity(uid={self.uid}, email={self.email}, role={self.role})"


class CurrentTeacher:
    """Authenticated teacher info attached to teacher-only requests."""

    def __init__(self, uid: str, email: str | None, name: str | None, institute_id: str):
        self.uid = uid
        self.teacher_id = f"teacher:{uid}"
        self.email = email
        self.name = name
        self.role = "teacher"
        self.institute_id = institute_id

    def __repr__(self):
        return (
            f"CurrentTeacher(uid={self.uid}, email={self.email}, "
            f"institute_id={self.institute_id})"
        )


class CurrentAdmin:
    """Authenticated admin identity for institute management endpoints."""

    def __init__(self, uid: str, email: str | None, name: str | None, role: str):
        self.uid = uid
        self.admin_id = f"admin:{uid}"
        self.email = email
        self.name = name
        self.role = role

    def __repr__(self):
        return f"CurrentAdmin(uid={self.uid}, email={self.email}, role={self.role})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    REQUIRED auth — raises 401 if no valid token.
    Use for: insights, progress tracking, student dashboard.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        decoded = verify_id_token(credentials.credentials)
    except Exception:
        logger.exception("Token verification failed in get_current_user")
        raise HTTPException(status_code=401, detail="Invalid token")

    role = str(decoded.get("role", "student")).lower()
    # Claims are the source of truth for authorization.
    # Empty/missing role defaults to student for backwards compatibility.
    if role not in {"", "student"}:
        raise HTTPException(status_code=403, detail="Student role required")

    user = CurrentUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role="student",
    )
    return user


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentIdentity:
    """
    REQUIRED auth identity dependency with no domain side-effects.
    Use for shared profile/account routes that should work for all roles.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        decoded = verify_id_token(credentials.credentials)
    except Exception:
        logger.exception("Token verification failed in get_authenticated_user")
        raise HTTPException(status_code=401, detail="Invalid token")

    return CurrentIdentity(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role=str(decoded.get("role", "student")).lower() or "student",
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser | None:
    """
    OPTIONAL auth — returns None if no token (anonymous access).
    Use for: teaching, content browsing, animations.

    If a token IS present it still verifies it and returns the user,
    enabling personalization (insights, prerequisite-aware flow).
    If no token, returns None — teaching proceeds without personalization.
    """
    if credentials is None:
        return None

    try:
        decoded = verify_id_token(credentials.credentials)
    except Exception:
        return None  # Bad token = treat as anonymous, don't block teaching

    role = str(decoded.get("role", "student")).lower()
    # Optional learner context is only valid for student identities.
    # Elevated roles should not be auto-mapped into Student graph flows.
    if role not in {"", "student"}:
        return None

    user = CurrentUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role="student",
    )
    return user


async def get_current_teacher(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentTeacher:
    """
    REQUIRED teacher auth — raises when token is missing/invalid or claims are not teacher-scoped.
    Uses Firebase claims as source of truth:
      - role must be "teacher"
      - institute_id must be present
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        decoded = verify_id_token(credentials.credentials)
    except Exception:
        logger.exception("Token verification failed in get_current_teacher")
        raise HTTPException(status_code=401, detail="Invalid token")

    role = str(decoded.get("role", "")).lower()
    institute_id = decoded.get("institute_id")
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher role required")
    if not institute_id:
        raise HTTPException(status_code=403, detail="Missing institute_id claim")

    teacher = CurrentTeacher(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        institute_id=str(institute_id),
    )
    return teacher


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentAdmin:
    """
    REQUIRED admin auth.
    Accepts Firebase role claims: 'admin' or 'superadmin'.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        decoded = verify_id_token(credentials.credentials)
    except Exception:
        logger.exception("Token verification failed in get_current_admin")
        raise HTTPException(status_code=401, detail="Invalid token")

    role = str(decoded.get("role", "")).lower()
    if role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin role required")

    return CurrentAdmin(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role=role,
    )
