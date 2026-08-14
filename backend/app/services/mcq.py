"""MCQ generation contract normalization shared by assessment surfaces."""

from __future__ import annotations

from typing import Any


OPTION_LABELS = ("A", "B", "C", "D")
MCQ_MAX_TOKENS = 1200

_OPTION_PROPERTIES = {
    label: {"type": "string", "minLength": 1} for label in OPTION_LABELS
}
_BASE_MCQ_PROPERTIES: dict[str, Any] = {
    "question": {"type": "string", "minLength": 1},
    "options": {
        "type": "object",
        "properties": _OPTION_PROPERTIES,
        "required": list(OPTION_LABELS),
        "additionalProperties": False,
    },
    "correct_answer": {"type": "string", "enum": list(OPTION_LABELS)},
    "explanation": {"type": "string", "minLength": 1},
}
INSIGHT_MCQ_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": _BASE_MCQ_PROPERTIES,
    "required": ["question", "options", "correct_answer", "explanation"],
    "additionalProperties": False,
}
SECTION_MCQ_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        **_BASE_MCQ_PROPERTIES,
        "subsection_id": {"type": "string", "minLength": 1},
        "key_terms": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 1,
            "maxItems": 6,
        },
    },
    "required": [
        "question",
        "options",
        "correct_answer",
        "explanation",
        "subsection_id",
        "key_terms",
    ],
    "additionalProperties": False,
}


def normalize_mcq_options(data: dict[str, Any]) -> dict[str, Any]:
    """Accept the requested nested shape and Nemotron's flat A-D variant."""
    normalized = dict(data)
    raw_options = normalized.get("options")
    if isinstance(raw_options, dict):
        candidate = {label: raw_options.get(label) for label in OPTION_LABELS}
    else:
        candidate = {label: normalized.get(label) for label in OPTION_LABELS}

    if all(isinstance(value, str) and value.strip() for value in candidate.values()):
        normalized["options"] = {
            label: candidate[label].strip() for label in OPTION_LABELS
        }
    return normalized


def has_complete_mcq_options(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(value.get(label), str) and value[label].strip()
        for label in OPTION_LABELS
    )


def mcq_validation_errors(
    data: dict[str, Any],
    *,
    require_subsection: bool = False,
    require_key_terms: bool = False,
) -> list[str]:
    """Return safe field-level contract failures without logging learner content."""
    errors: list[str] = []
    if not isinstance(data.get("question"), str) or not data["question"].strip():
        errors.append("missing_question")

    options = data.get("options")
    if not isinstance(options, dict):
        errors.append("invalid_options_object")
    else:
        errors.extend(
            f"missing_option_{label}"
            for label in OPTION_LABELS
            if not isinstance(options.get(label), str) or not options[label].strip()
        )

    if data.get("correct_answer") not in OPTION_LABELS:
        errors.append("invalid_correct_answer")
    if not isinstance(data.get("explanation"), str) or not data["explanation"].strip():
        errors.append("missing_explanation")
    if require_subsection and (
        not isinstance(data.get("subsection_id"), str)
        or not data["subsection_id"].strip()
    ):
        errors.append("missing_subsection_id")
    if require_key_terms and not isinstance(data.get("key_terms"), list):
        errors.append("invalid_key_terms")
    return errors
