from __future__ import annotations

import unittest

from evals.scorers import score_mcq, score_output


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


if __name__ == "__main__":
    unittest.main()
