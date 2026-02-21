"""
Auth middleware — extracts and verifies Firebase ID tokens from requests.

Two dependency functions:
  - get_current_user:   REQUIRED auth — 401 if no token (for insights, progress)
  - get_optional_user:  OPTIONAL auth — returns None if no token (for teaching)
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.firebase import verify_id_token
from app.database import write_query

# Extracts "Bearer <token>" from Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)


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


def ensure_student(user: "CurrentUser") -> None:
    """
    Idempotent MERGE of Student node in Neo4j.
    Called on every authenticated request — safe to call repeatedly.
    Creates the node on first login; updates name/email on subsequent logins.
    """
    write_query(
        """
        MERGE (s:Student {id: $student_id})
        ON CREATE SET s.name = $name,
                      s.email = $email,
                      s.role = $role,
                      s.created_at = datetime()
        ON MATCH SET  s.name = $name,
                      s.email = $email,
                      s.role = $role
        """,
        student_id=user.student_id,
        name=user.name or "",
        email=user.email or "",
        role=user.role or "student",
    )


def ensure_teacher(teacher: "CurrentTeacher") -> None:
    """
    Idempotent MERGE of Teacher node for auditability and ownership trace.
    Auth still relies on Firebase claims.
    """
    write_query(
        """
        MERGE (t:Teacher {id: $teacher_id})
        ON CREATE SET t.uid = $uid,
                      t.name = $name,
                      t.email = $email,
                      t.institute_id = $institute_id,
                      t.created_at = datetime()
        ON MATCH SET  t.name = $name,
                      t.email = $email,
                      t.institute_id = $institute_id,
                      t.updated_at = datetime()
        """,
        teacher_id=teacher.teacher_id,
        uid=teacher.uid,
        name=teacher.name or "",
        email=teacher.email or "",
        institute_id=teacher.institute_id,
    )


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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user = CurrentUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role=decoded.get("role", "student"),
    )
    ensure_student(user)
    return user


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

    user = CurrentUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role=decoded.get("role", "student"),
    )
    ensure_student(user)
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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

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
    ensure_teacher(teacher)
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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    role = str(decoded.get("role", "")).lower()
    if role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin role required")

    return CurrentAdmin(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        role=role,
    )
