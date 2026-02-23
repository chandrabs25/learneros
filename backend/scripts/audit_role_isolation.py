"""
Read-only role/data separation audit for LearnerOS graph.

Usage:
  python -m scripts.audit_role_isolation

Exit codes:
  0 -> no findings
  1 -> one or more findings
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import read_query  # noqa: E402


CHECKS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "Student nodes with elevated roles",
        """
        MATCH (s:Student)
        WHERE toLower(coalesce(s.role, 'student')) IN ['teacher', 'admin', 'superadmin']
        RETURN count(*) AS c
        """,
        (
            "Student nodes should represent learners only. Elevated roles belong in claims/Teacher nodes.",
        ),
    ),
    (
        "Teacher nodes missing BELONGS_TO institute",
        """
        MATCH (t:Teacher)
        WHERE NOT (t)-[:BELONGS_TO]->(:Institute)
        RETURN count(*) AS c
        """,
        (
            "Teacher institute ownership is required for safe scoping.",
        ),
    ),
    (
        "Teacher institute property mismatches BELONGS_TO",
        """
        MATCH (t:Teacher)-[:BELONGS_TO]->(i:Institute)
        WHERE t.institute_id IS NOT NULL AND t.institute_id <> i.id
        RETURN count(*) AS c
        """,
        (
            "Teacher.institute_id should match linked Institute id.",
        ),
    ),
    (
        "Insights attached to non-student-role Student nodes",
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(:Insight)
        WHERE toLower(coalesce(s.role, 'student')) <> 'student'
        RETURN count(*) AS c
        """,
        (
            "Learner insights should only belong to learner accounts.",
        ),
    ),
    (
        "Tutor sessions attached to non-student-role Student nodes",
        """
        MATCH (s:Student)-[:HAS_TUTOR_SESSION]->(:TutorSession)
        WHERE toLower(coalesce(s.role, 'student')) <> 'student'
        RETURN count(*) AS c
        """,
        (
            "Student tutor sessions should not be attached to teacher/admin identities.",
        ),
    ),
]


def run_check(name: str, cypher: str) -> int:
    rows = read_query(cypher)
    return int((rows[0] or {}).get("c") or 0) if rows else 0


def main() -> int:
    print("=== Role Isolation Audit ===")
    findings = 0

    for name, cypher, guidance in CHECKS:
        count = run_check(name, cypher)
        status = "OK" if count == 0 else "FINDING"
        print(f"[{status}] {name}: {count}")
        if count > 0:
            findings += 1
            for line in guidance:
                print(f"  - {line}")

    print("\nSummary:")
    if findings == 0:
        print("No role-isolation inconsistencies detected.")
        return 0

    print(f"Detected {findings} failing check(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
