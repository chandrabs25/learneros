"""
Backfill stored Student.embedding vectors from active Insight embeddings.

Usage:
  cd backend
  python -m scripts.backfill_student_embeddings
  python -m scripts.backfill_student_embeddings --limit 500 --only-missing
"""

import argparse
import os
import sys
import time

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import read_query  # noqa: E402
from app.services.student_embeddings import update_student_embedding  # noqa: E402


def fetch_student_ids(limit: int, *, only_missing: bool) -> list[str]:
    limit_clause = "LIMIT $limit" if limit > 0 else ""
    rows = read_query(
        f"""
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {{is_active: true}})
        WHERE i.embedding IS NOT NULL
          AND ($only_missing = false OR s.embedding IS NULL OR s.embedding_source_count IS NULL)
        RETURN DISTINCT s.id AS student_id
        ORDER BY student_id
        {limit_clause}
        """,
        limit=limit,
        only_missing=only_missing,
    )
    return [str(r["student_id"]) for r in rows if r.get("student_id")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Student.embedding from active insight embeddings")
    parser.add_argument("--limit", type=int, default=1000, help="Max students to backfill; use 0 for all")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Sleep between students to reduce DB pressure")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only process students without a stored embedding/source count",
    )
    args = parser.parse_args()

    student_ids = fetch_student_ids(args.limit, only_missing=args.only_missing)
    if not student_ids:
        print("No students with active embedded insights found.")
        return

    print(f"Backfilling student embeddings for {len(student_ids)} student(s)")
    updated = 0
    cleared = 0

    for idx, student_id in enumerate(student_ids, start=1):
        built = update_student_embedding(student_id)
        if built is None:
            cleared += 1
        else:
            updated += 1

        print(f"  processed {idx}/{len(student_ids)} updated={updated} cleared={cleared}")
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000)

    print(f"Backfill complete. updated={updated} cleared={cleared}")


if __name__ == "__main__":
    main()
