"""MCQ generation contract normalization shared by assessment surfaces."""

from __future__ import annotations

from typing import Any


OPTION_LABELS = ("A", "B", "C", "D")


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
