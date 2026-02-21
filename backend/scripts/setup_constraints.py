"""
setup_constraints.py
--------------------
Run once (or on each deploy) to ensure all Neo4j constraints exist.
Safe to re-run — every statement uses IF NOT EXISTS.

Usage (from the backend/ directory):
    python -m scripts.setup_constraints
"""

import sys
import os

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import get_driver  # noqa: E402  (after sys.path fix)

# ---------------------------------------------------------------------------
# Constraints to create
# Each entry: (label, property, constraint_name, kind)
# kind: "UNIQUE" | "NOT NULL"   (NOT NULL = property existence)
# ---------------------------------------------------------------------------
CONSTRAINTS: list[tuple[str, str, str, str]] = [
    # ── Curriculum nodes (populated by data-load scripts) ──────────────
    ("Textbook",  "id",    "textbook_id_unique",  "UNIQUE"),
    ("Subject",   "id",    "subject_id_unique",   "UNIQUE"),
    ("Chapter",   "id",    "chapter_id_unique",   "UNIQUE"),
    ("Section",   "id",    "section_id_unique",   "UNIQUE"),
    ("Subsection","id",    "subsection_id_unique","UNIQUE"),
    ("Concept",   "id",    "concept_id_unique",   "UNIQUE"),
    ("Exercise",  "id",    "exercise_id_unique",  "UNIQUE"),
    ("Institute", "id",    "institute_id_unique", "UNIQUE"),

    # ── Runtime-created nodes ──────────────────────────────────────────
    ("Student",   "id",    "student_id_unique",   "UNIQUE"),
    ("Insight",   "id",    "insight_id_unique",   "UNIQUE"),
    ("TutorSession", "id", "tutor_session_id_unique", "UNIQUE"),
    ("TutorMessage", "id", "tutor_message_id_unique", "UNIQUE"),
    ("Teacher", "id", "teacher_id_unique", "UNIQUE"),
    ("TeacherApplication", "id", "teacher_application_id_unique", "UNIQUE"),
    ("StudentClusterSnapshot", "id", "student_cluster_snapshot_id_unique", "UNIQUE"),
    ("StudentCluster", "id", "student_cluster_id_unique", "UNIQUE"),

    # ── NOT NULL guards on critical properties ─────────────────────────
    ("Student",   "id",    "student_id_exists",   "NOT NULL"),
    ("Institute", "id",    "institute_id_exists", "NOT NULL"),
    ("Insight",   "id",    "insight_id_exists",   "NOT NULL"),
    ("Insight",   "type",  "insight_type_exists", "NOT NULL"),
    ("Insight",   "category", "insight_cat_exists","NOT NULL"),
    ("Insight",   "is_active","insight_active_exists","NOT NULL"),
    ("TutorSession", "id", "tutor_session_id_exists", "NOT NULL"),
    ("TutorMessage", "id", "tutor_message_id_exists", "NOT NULL"),
    ("Teacher", "id", "teacher_id_exists", "NOT NULL"),
    ("TeacherApplication", "id", "teacher_application_id_exists", "NOT NULL"),
    ("TeacherApplication", "status", "teacher_application_status_exists", "NOT NULL"),
    ("StudentClusterSnapshot", "id", "student_cluster_snapshot_id_exists", "NOT NULL"),
    ("StudentCluster", "id", "student_cluster_id_exists", "NOT NULL"),
]

INDEXES: list[tuple[str, str, str]] = [
    ("Student", "institute_id", "student_institute_idx"),
    ("Student", "grade", "student_grade_idx"),
    ("Student", "role", "student_role_idx"),
    ("Insight", "is_active", "insight_is_active_idx"),
    ("Insight", "type", "insight_type_idx"),
    ("Insight", "created_at", "insight_created_at_idx"),
]


def cypher_for(label: str, prop: str, name: str, kind: str) -> str:
    if kind == "UNIQUE":
        return (
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )
    elif kind == "NOT NULL":
        return (
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL"
        )
    else:
        raise ValueError(f"Unknown constraint kind: {kind}")


def main() -> None:
    driver = get_driver()
    ok = 0
    failed = 0

    with driver.session() as session:
        for label, prop, name, kind in CONSTRAINTS:
            cypher = cypher_for(label, prop, name, kind)
            try:
                session.run(cypher)
                print(f"  ✓  {name}  ({kind} on {label}.{prop})")
                ok += 1
            except Exception as exc:
                print(f"  ✗  {name}  — {exc}")
                failed += 1

        for label, prop, name in INDEXES:
            cypher = f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
            try:
                session.run(cypher)
                print(f"  ✓  {name}  (INDEX on {label}.{prop})")
                ok += 1
            except Exception as exc:
                print(f"  ✗  {name}  — {exc}")
                failed += 1

    print(f"\n{'─'*50}")
    print(f"Applied: {ok}   Failed: {failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
