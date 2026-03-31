"""
Build teacher dashboard student clusters from active insight embeddings.

This is a thin CLI wrapper around :mod:`app.services.clustering_runner`.

Usage:
  python -m scripts.build_teacher_clusters --institute-id institute:1
  python -m scripts.build_teacher_clusters --all
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.clustering_runner import build_for_institute, fetch_institute_ids  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build teacher dashboard student clusters.")
    parser.add_argument("--institute-id", type=str, default=None)
    parser.add_argument("--all", action="store_true", help="Build for all institutes found on Student nodes")
    parser.add_argument("--k", type=int, default=None, help="Optional cluster count override")
    parser.add_argument("--min-students", type=int, default=3)
    parser.add_argument("--min-insights-per-student", type=int, default=3)
    parser.add_argument("--min-vector-norm", type=float, default=0.001)
    parser.add_argument("--hdbscan-min-cluster-size", type=int, default=2)
    parser.add_argument("--hdbscan-min-samples", type=int, default=None)
    args = parser.parse_args()

    if not args.all and not args.institute_id:
        parser.error("Provide --institute-id <id> or --all")

    institute_ids = [args.institute_id] if args.institute_id else fetch_institute_ids()
    if not institute_ids:
        print(json.dumps({"status": "no_institutes_found"}))
        return 0

    any_fail = False
    for iid in institute_ids:
        try:
            result = build_for_institute(
                iid,
                k_override=args.k,
                min_students=args.min_students,
                min_insights_per_student=args.min_insights_per_student,
                min_vector_norm=args.min_vector_norm,
                hdbscan_min_cluster_size=args.hdbscan_min_cluster_size,
                hdbscan_min_samples=args.hdbscan_min_samples,
            )
            print(json.dumps(result))
            if result.get("status") == "error":
                any_fail = True
        except Exception as exc:
            any_fail = True
            err_result = {
                "institute_id": iid,
                "status": "error",
                "engine_version": "semantic_v2",
                "error": str(exc),
            }
            print(json.dumps(err_result))
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
