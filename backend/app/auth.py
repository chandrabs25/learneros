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
                      s.created_at = datetime()
        ON MATCH SET  s.name = $name,
                      s.email = $email
        """,
        student_id=user.student_id,
        name=user.name or "",
        email=user.email or "",
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
