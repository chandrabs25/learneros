from __future__ import annotations

import unittest
from pathlib import Path

from evals.dataset_contract import is_runnable, load_jsonl, redact_text, validate_case
from evals.promote import promote_records
from evals.scorers import score_mcq, score_output, score_reconciliation, score_retrieval


EVAL_ROOT = Path(__file__).resolve().parents[1] / "evals"


class EvalScorerTests(unittest.TestCase):
    def test_valid_mcq_passes_all_checks(self) -> None:
        score = score_mcq(
            {
                "question": "Which expression represents work by a constant force?",
                "options": {"A": "Fd cos(theta)", "B": "Fd sin(theta)", "C": "F/d", "D": "F+d"},
                "correct_answer": "A",
                "explanation": "Work is the force-displacement dot product, which introduces the cosine of their angle.",
                "subsection_id": "section:1",
                "key_terms": ["work", "force", "displacement"],
            },
            {"subsection_id": "section:1"},
        )
        self.assertEqual(score.value, 1.0)

    def test_duplicate_options_fail(self) -> None:
        score = score_mcq(
            {
                "question": "Which expression represents work by a constant force?",
                "options": {"A": "Fd", "B": "Fd", "C": "F/d", "D": "F+d"},
                "correct_answer": "A",
                "explanation": "Work is the force-displacement dot product, which introduces the cosine of their angle.",
                "subsection_id": "section:1",
                "key_terms": ["work", "force", "displacement"],
            },
            {"subsection_id": "section:1"},
        )
        self.assertLess(score.value, 1.0)
        self.assertFalse(next(check for check in score.checks if check.name == "options_unique").passed)

    def test_unknown_task_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            score_output("unknown", {}, {})

    def test_reconciliation_scores_expected_decision_and_preserved_facts(self) -> None:
        score = score_reconciliation(
            {
                "action": "MERGE",
                "type": "PARTIAL_UNDERSTANDING",
                "content": (
                    "The student knows that net work equals change in kinetic energy, "
                    "but must explain why variable forces require integration."
                ),
            },
            {
                "action": "MERGE",
                "type": "PARTIAL_UNDERSTANDING",
                "required_facts": [
                    "net work equals change in kinetic energy",
                    "variable forces require integration",
                ],
                "forbidden_facts": ["continuous force is required"],
            },
        )
        self.assertEqual(score.value, 1.0)

    def test_retrieval_rejects_forbidden_distractor(self) -> None:
        score = score_retrieval(
            {"selected_ids": ["insight:inertia", "insight:photosynthesis"]},
            {
                "relevant_ids": ["insight:inertia"],
                "forbidden_ids": ["insight:photosynthesis"],
                "minimum_recall": 1.0,
                "max_results": 1,
            },
        )
        self.assertLess(score.value, 1.0)

    def test_pending_candidate_is_not_runnable(self) -> None:
        case = {
            "id": "pending-case",
            "task": "tutor",
            "prompt": "Explain inertia in a way that can be reviewed later.",
            "review": {"status": "pending"},
        }
        validate_case(case)
        self.assertFalse(is_runnable(case))

    def test_approved_reconciliation_requires_expected_labels(self) -> None:
        case = {
            "id": "incomplete-reconciliation",
            "task": "reconciliation",
            "prompt": "Reconcile the observations and return JSON.",
            "expected": {},
            "review": {"status": "approved"},
        }
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_redaction_removes_direct_identifiers(self) -> None:
        redacted = redact_text("Email learner@example.com or call +91 98765 43210 at https://example.com/profile")
        self.assertNotIn("learner@example.com", redacted)
        self.assertNotIn("98765", redacted)
        self.assertNotIn("https://example.com", redacted)

    def test_promotion_only_includes_valid_approved_cases(self) -> None:
        records = [
            {
                "id": "approved-tutor",
                "task": "tutor",
                "prompt": "Explain inertia using a concrete example for a learner.",
                "expected": {"required_terms": ["inertia"]},
                "candidate_output": {"text": "private draft"},
                "review": {
                    "status": "approved",
                    "reviewer": "reviewer-1",
                    "needs_fields": ["expected.required_terms"],
                },
            },
            {
                "id": "pending-tutor",
                "task": "tutor",
                "prompt": "Explain momentum using a concrete example for a learner.",
                "review": {"status": "pending"},
            },
        ]
        promoted, stats = promote_records(records)
        self.assertEqual(stats, {"approved": 1, "pending": 1, "rejected": 0})
        self.assertEqual([item["id"] for item in promoted], ["approved-tutor"])
        self.assertNotIn("candidate_output", promoted[0])
        self.assertNotIn("needs_fields", promoted[0]["review"])

    def test_checked_in_core_suite_scores_cleanly_offline(self) -> None:
        cases = load_jsonl(EVAL_ROOT / "datasets" / "core.jsonl")
        outputs = {
            record["id"]: record["output"]
            for record in load_jsonl(EVAL_ROOT / "fixtures" / "core_responses.jsonl")
        }
        self.assertEqual(len(cases), len(outputs))
        for case in cases:
            validate_case(case, require_approved=True)
            with self.subTest(case=case["id"]):
                score = score_output(case["task"], outputs[case["id"]], case["expected"])
                self.assertEqual(score.value, 1.0)


if __name__ == "__main__":
    unittest.main()
