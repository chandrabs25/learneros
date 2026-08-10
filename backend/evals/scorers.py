"""Deterministic quality gates for LearnerOS model outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


VALID_INSIGHT_TYPES = {"COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"}
VALID_RECONCILIATION_ACTIONS = {"MERGE", "REPLACE"}


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class Score:
    value: float
    checks: list[Check]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.value,
            "checks": [asdict(check) for check in self.checks],
        }


def _nonempty(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _key_terms(output: dict[str, Any]) -> bool:
    terms = output.get("key_terms")
    return (
        isinstance(terms, list)
        and 3 <= len(terms) <= 6
        and all(_nonempty(term) for term in terms)
    )


def _expected_id(output: dict[str, Any], expected: dict[str, Any], field: str) -> bool:
    wanted = expected.get(field)
    return wanted is None or output.get(field) == wanted


def _finalize(checks: list[Check]) -> Score:
    passed = sum(1 for check in checks if check.passed)
    return Score(round(passed / len(checks), 4) if checks else 0.0, checks)


def score_question(output: dict[str, Any], expected: dict[str, Any]) -> Score:
    return _finalize(
        [
            Check("question_present", _nonempty(output.get("question"), 20)),
            Check("subsection_matches", _expected_id(output, expected, "subsection_id")),
            Check("hint_present", _nonempty(output.get("hint"), 10)),
            Check("key_terms_valid", _key_terms(output)),
        ]
    )


def score_mcq(output: dict[str, Any], expected: dict[str, Any]) -> Score:
    options = output.get("options")
    option_values = list(options.values()) if isinstance(options, dict) else []
    correct = output.get("correct_answer")
    return _finalize(
        [
            Check("question_present", _nonempty(output.get("question"), 20)),
            Check("four_labeled_options", isinstance(options, dict) and set(options) == {"A", "B", "C", "D"}),
            Check("options_nonempty", len(option_values) == 4 and all(_nonempty(value) for value in option_values)),
            Check("options_unique", len(option_values) == 4 and len(set(option_values)) == 4),
            Check("correct_answer_valid", correct in {"A", "B", "C", "D"} and isinstance(options, dict) and correct in options),
            Check("explanation_present", _nonempty(output.get("explanation"), 20)),
            Check("subsection_matches", _expected_id(output, expected, "subsection_id")),
            Check("key_terms_valid", _key_terms(output)),
        ]
    )


def score_insight(output: dict[str, Any], expected: dict[str, Any]) -> Score:
    expected_concepts = set(expected.get("concept_ids") or [])
    insights = output.get("insights")
    insights = insights if isinstance(insights, list) else []
    types_valid = all(item.get("type") in VALID_INSIGHT_TYPES for item in insights if isinstance(item, dict))
    concepts_valid = all(
        not expected_concepts or item.get("concept_id") in expected_concepts
        for item in insights
        if isinstance(item, dict)
    )
    content_valid = all(_nonempty(item.get("content"), 15) for item in insights if isinstance(item, dict))
    minimum_insights = int(expected.get("minimum_insights", 0))
    return _finalize(
        [
            Check("insights_is_list", isinstance(output.get("insights"), list)),
            Check("minimum_insights", len(insights) >= minimum_insights),
            Check("insight_types_valid", types_valid),
            Check("concept_ids_valid", concepts_valid),
            Check("insight_content_present", content_valid),
        ]
    )


def score_tutor(output: dict[str, Any], expected: dict[str, Any]) -> Score:
    text = output.get("text")
    required_terms = [str(term).casefold() for term in expected.get("required_terms") or []]
    normalized = str(text or "").casefold()
    return _finalize(
        [
            Check("answer_present", _nonempty(text, 40)),
            Check("required_terms_present", all(term in normalized for term in required_terms)),
        ]
    )


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def score_reconciliation(output: dict[str, Any], expected: dict[str, Any]) -> Score:
    action = str(output.get("action") or "").upper()
    insight_type = str(output.get("type") or "").upper()
    content = output.get("content")
    normalized = _normalized_text(content)
    required_facts = [_normalized_text(item) for item in expected.get("required_facts") or []]
    forbidden_facts = [_normalized_text(item) for item in expected.get("forbidden_facts") or []]
    expected_action = str(expected.get("action") or "").upper()
    expected_type = str(expected.get("type") or "").upper()
    return _finalize(
        [
            Check("action_valid", action in VALID_RECONCILIATION_ACTIONS),
            Check("action_matches", not expected_action or action == expected_action),
            Check("type_valid", insight_type in VALID_INSIGHT_TYPES),
            Check("type_matches", not expected_type or insight_type == expected_type),
            Check("content_present", _nonempty(content, 20)),
            Check("required_facts_preserved", all(fact in normalized for fact in required_facts)),
            Check("forbidden_facts_absent", all(fact not in normalized for fact in forbidden_facts)),
        ]
    )


def score_retrieval(output: dict[str, Any], expected: dict[str, Any]) -> Score:
    raw_ids = output.get("selected_ids")
    selected = [str(value) for value in raw_ids] if isinstance(raw_ids, list) else []
    relevant = {str(value) for value in expected.get("relevant_ids") or []}
    forbidden = {str(value) for value in expected.get("forbidden_ids") or []}
    minimum_recall = float(expected.get("minimum_recall", 1.0 if relevant else 0.0))
    recall = len(relevant.intersection(selected)) / len(relevant) if relevant else 1.0
    max_results = int(expected.get("max_results", len(selected) or 1))
    return _finalize(
        [
            Check("selected_ids_is_list", isinstance(raw_ids, list)),
            Check("selected_ids_unique", len(selected) == len(set(selected))),
            Check("minimum_recall", recall >= minimum_recall, f"recall={recall:.3f}"),
            Check("forbidden_ids_absent", forbidden.isdisjoint(selected)),
            Check("result_limit_respected", len(selected) <= max_results),
        ]
    )


def score_output(task: str, output: dict[str, Any], expected: dict[str, Any]) -> Score:
    scorers = {
        "question": score_question,
        "mcq": score_mcq,
        "insight": score_insight,
        "tutor": score_tutor,
        "reconciliation": score_reconciliation,
        "retrieval": score_retrieval,
    }
    try:
        scorer = scorers[task]
    except KeyError as exc:
        raise ValueError(f"Unsupported eval task: {task}") from exc
    return scorer(output, expected)
