"""
Institutes API — fetch available institutes and set student's institute.

Routes:
  GET   /api/institutes                → list all institutes (mock data)
  PATCH /api/students/me/institute     → set the student's institute (auth required)
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user, CurrentUser
from app.database import read_query, write_query

router = APIRouter(prefix="/api", tags=["institutes"])

# ── Mock data (replace with DB query when real institute data is available) ───

MOCK_INSTITUTES = [
    {
        "id": "institute:1",
        "name": "Institute 1",
        "location": "Hyderabad, India",
        "description": "Premier coaching institute for JEE & NEET preparation",
        "logo": None,
    },
]


# ── GET /api/institutes ────────────────────────────────────────────────────────

@router.get("/institutes")
async def list_institutes():
    """Return all available institutes. No auth required."""
    return MOCK_INSTITUTES


# ── PATCH /api/students/me/institute ──────────────────────────────────────────

class SetInstituteBody(BaseModel):
    institute_id: str


@router.patch("/students/me/institute")
async def set_student_institute(
    body: SetInstituteBody,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Store the student's selected institute on their Student node in Neo4j.
    Creates the relationship: (Student)-[:ENROLLED_IN]->(Institute)
    Uses a mock institute node for now — replace with real Institute nodes later.
    """
    write_query(
        """
        MATCH (s:Student {id: $student_id})
        SET s.institute_id = $institute_id
        """,
        student_id=user.student_id,
        institute_id=body.institute_id,
    )
    return {"status": "ok", "institute_id": body.institute_id}


# ── GET /api/students/me/institute ─────────────────────────────────────────────

@router.get("/students/me/institute")
async def get_student_institute(
    user: CurrentUser = Depends(get_current_user),
):
    """Return the student's currently selected institute, if any."""
    rows = read_query(
        "MATCH (s:Student {id: $student_id}) RETURN s.institute_id AS institute_id",
        student_id=user.student_id,
    )
    institute_id = rows[0]["institute_id"] if rows else None

    if not institute_id:
        return {"institute": None}

    institute = next((i for i in MOCK_INSTITUTES if i["id"] == institute_id), None)
    return {"institute": institute}
