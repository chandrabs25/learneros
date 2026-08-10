"""Export anonymized internal eval candidates from Neo4j for human review."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.database import close_driver, read_query
from evals.dataset_contract import redact_text, stable_case_id, write_jsonl


def _review(source: str, *needs_fields: str, note: str) -> dict[str, Any]:
    return {
        "status": "pending",
        "source": source,
        "needs_fields": list(needs_fields),
        "note": note,
    }


def curriculum_candidates(limit: int) -> list[dict[str, Any]]:
    rows = read_query(
        """
        MATCH (sec:Section)-[:CONTAINS]->(ss:Subsection)
        OPTIONAL MATCH (sec)-[:REQUIRES]->(c:Concept)
        WITH sec, ss,
             [item IN collect(DISTINCT {id: c.id, name: c.name}) WHERE item.id IS NOT NULL] AS concepts
        WHERE ss.content_text IS NOT NULL AND trim(ss.content_text) <> ''
        RETURN sec.id AS section_id,
               ss.id AS subsection_id,
               ss.title AS subsection_title,
               ss.content_text AS content,
               concepts
        ORDER BY sec.id, ss.id
        LIMIT $limit
        """,
        limit=limit,
    )
    records: list[dict[str, Any]] = []
    for row in rows:
        subsection_id = str(row.get("subsection_id") or "")
        content = redact_text(row.get("content"))
        concepts = row.get("concepts") or []
        concept_ids = [item.get("id") for item in concepts if isinstance(item, dict) and item.get("id")]
        context = content[:6000]
        records.extend(
            [
                {
                    "id": stable_case_id("question", subsection_id),
                    "task": "question",
                    "prompt": (
                        "Using only the curriculum passage below, create one comprehension question. "
                        f"Return JSON with question, subsection_id set to {subsection_id}, hint, and 3-6 key_terms.\n\n"
                        f"Passage:\n{context}"
                    ),
                    "expected": {"subsection_id": subsection_id},
                    "metadata": {"section_id": row.get("section_id"), "concept_ids": concept_ids},
                    "review": _review(
                        "neo4j_curriculum",
                        "review.status",
                        note="Verify the passage is sufficient, unambiguous, and worth retaining before approval.",
                    ),
                },
                {
                    "id": stable_case_id("mcq", subsection_id),
                    "task": "mcq",
                    "prompt": (
                        "Using only the curriculum passage below, create one conceptual MCQ. Return JSON with "
                        "question, options A-D, correct_answer, explanation, "
                        f"subsection_id set to {subsection_id}, and 3-6 key_terms.\n\nPassage:\n{context}"
                    ),
                    "expected": {"subsection_id": subsection_id},
                    "metadata": {"section_id": row.get("section_id"), "concept_ids": concept_ids},
                    "review": _review(
                        "neo4j_curriculum",
                        "review.status",
                        note="Verify the source supports one defensible answer before approval.",
                    ),
                },
            ]
        )
    return records


def reconciliation_candidates(limit: int) -> list[dict[str, Any]]:
    rows = read_query(
        """
        MATCH (current:Insight)-[:SUPERSEDES]->(old:Insight)
        OPTIONAL MATCH (current)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (current)-[:ABOUT_SOURCE]->(src)
        RETURN current.id AS current_id,
               current.type AS current_type,
               current.content AS current_content,
               old.id AS old_id,
               old.type AS old_type,
               old.content AS old_content,
               c.id AS concept_id,
               src.id AS source_id
        ORDER BY current.created_at DESC
        LIMIT $limit
        """,
        limit=limit,
    )
    records: list[dict[str, Any]] = []
    for row in rows:
        old = {"type": row.get("old_type"), "content": redact_text(row.get("old_content"))}
        current = {
            "type": row.get("current_type"),
            "content": redact_text(row.get("current_content")),
        }
        records.append(
            {
                "id": stable_case_id("reconciliation-history", row.get("current_id"), row.get("old_id")),
                "task": "reconciliation",
                "prompt": (
                    "Historical candidate only. A reviewer must reconstruct the missing raw new evidence before this "
                    "case can become ground truth. Return JSON with action, type, and content.\n\n"
                    f"OLD={json.dumps(old, ensure_ascii=True)}\nCURRENT_RECONCILED={json.dumps(current, ensure_ascii=True)}"
                ),
                "candidate_output": current,
                "metadata": {"concept_id": row.get("concept_id"), "source_id": row.get("source_id")},
                "review": _review(
                    "neo4j_insight_lineage",
                    "input.new_insight",
                    "expected.action",
                    "expected.type",
                    "expected.required_facts",
                    note=(
                        "SUPERSEDES stores old and final states, not the raw incoming insight or model decision. "
                        "Do not approve until those labels are reconstructed from original assessment evidence."
                    ),
                ),
            }
        )
    return records


def conversation_candidates(limit: int) -> list[dict[str, Any]]:
    """Opt-in export: free-form tutor text can still contain sensitive prose after direct-identifier redaction."""
    message_rows = read_query(
        """
        MATCH (student:Student)-[:HAS_TUTOR_SESSION]->(sess:TutorSession)-[:HAS_MESSAGE]->(m:TutorMessage)
        RETURN elementId(student) AS student_key,
               sess.id AS session_id,
               m.id AS message_id,
               m.role AS role,
               m.content AS content,
               m.created_at AS created_at
        ORDER BY session_id, created_at
        LIMIT $limit
        """,
        limit=limit * 2,
    )
    insight_rows = read_query(
        """
        MATCH (student:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        RETURN elementId(student) AS student_key,
               i.id AS id,
               i.type AS type,
               i.content AS content,
               c.id AS concept_id
        """
    )
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in insight_rows:
        pools[str(row.get("student_key"))].append(
            {
                "id": row.get("id"),
                "content": redact_text(row.get("content")),
                "metadata": {"type": row.get("type"), "concept_id": row.get("concept_id")},
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in message_rows:
        grouped[str(row.get("session_id"))].append(row)

    records: list[dict[str, Any]] = []
    for session_id, messages in grouped.items():
        for index, message in enumerate(messages[:-1]):
            following = messages[index + 1]
            if message.get("role") != "user" or following.get("role") != "assistant":
                continue
            query = redact_text(message.get("content"))
            answer = redact_text(following.get("content"))
            student_key = str(message.get("student_key"))
            records.extend(
                [
                    {
                        "id": stable_case_id("tutor-history", session_id, message.get("message_id")),
                        "task": "tutor",
                        "prompt": query,
                        "candidate_output": {"text": answer},
                        "review": _review(
                            "neo4j_tutor_history",
                            "expected.required_terms",
                            "review.status",
                            note="Inspect for residual sensitive information and grade answer correctness before approval.",
                        ),
                    }
                ]
            )
            candidate_pool = pools.get(student_key, [])
            if candidate_pool:
                records.append(
                    {
                        "id": stable_case_id("retrieval-history", session_id, message.get("message_id")),
                        "task": "retrieval",
                        "input": {"query": query, "candidates": candidate_pool, "top_k": 4},
                        "review": _review(
                            "neo4j_tutor_history",
                            "expected.relevant_ids",
                            "expected.forbidden_ids",
                            "review.status",
                            note=(
                                "The runtime did not persist matched insight IDs. A reviewer must label relevance; "
                                "the active insight pool is only a candidate set."
                            ),
                        ),
                    }
                )
            if len(records) >= limit * 2:
                return records
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evals/private/candidates.jsonl"))
    parser.add_argument("--limit-per-source", type=int, default=100)
    parser.add_argument(
        "--include-conversations",
        action="store_true",
        help="Include redacted tutor text. This still requires manual privacy review.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit_per_source < 1:
        raise ValueError("--limit-per-source must be positive")
    try:
        records = curriculum_candidates(args.limit_per_source)
        records.extend(reconciliation_candidates(args.limit_per_source))
        if args.include_conversations:
            records.extend(conversation_candidates(args.limit_per_source))
        count = write_jsonl(args.output, records)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "candidates": count,
                    "review_status": "pending",
                    "conversations_included": args.include_conversations,
                },
                indent=2,
            )
        )
        return 0
    finally:
        close_driver()


if __name__ == "__main__":
    sys.exit(main())
