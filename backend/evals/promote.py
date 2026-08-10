"""Validate reviewed candidates and promote approved records to a golden JSONL."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from evals.dataset_contract import load_jsonl, review_status, validate_case, write_jsonl


PRIVATE_ONLY_FIELDS = {"candidate_output", "review_notes", "source_private"}


def promote_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    promoted: list[dict[str, Any]] = []
    stats = {"approved": 0, "pending": 0, "rejected": 0}
    seen_ids: set[str] = set()

    for source in records:
        status = review_status(source)
        if status is None:
            raise ValueError(f"Candidate {source.get('id', '<unknown>')} has no review status")
        stats[status] += 1
        if status != "approved":
            continue

        validate_case(source, require_approved=True)
        case_id = str(source["id"])
        if case_id in seen_ids:
            raise ValueError(f"Duplicate approved case id: {case_id}")
        seen_ids.add(case_id)

        clean = copy.deepcopy(source)
        for field in PRIVATE_ONLY_FIELDS:
            clean.pop(field, None)
        review = clean.get("review")
        if isinstance(review, dict):
            review.pop("needs_fields", None)
        promoted.append(clean)

    return promoted, stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Human-reviewed candidate JSONL")
    parser.add_argument("--output", type=Path, required=True, help="Golden dataset JSONL")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    promoted, stats = promote_records(load_jsonl(args.input))
    count = write_jsonl(args.output, promoted)
    print(json.dumps({"output": str(args.output), "promoted": count, **stats}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
