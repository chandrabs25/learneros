"""Dataset review, validation, redaction, and JSONL helpers for evals."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


SUPPORTED_TASKS = {"question", "mcq", "insight", "tutor", "reconciliation", "retrieval"}
REVIEW_STATUSES = {"pending", "approved", "rejected"}

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)


def stable_case_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def redact_text(value: Any) -> str:
    text = str(value or "")
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return _URL_RE.sub("[REDACTED_URL]", text)


def review_status(case: dict[str, Any]) -> str | None:
    review = case.get("review")
    if review is None:
        return None
    if not isinstance(review, dict):
        raise ValueError(f"Case {case.get('id', '<unknown>')} review must be an object")
    status = str(review.get("status") or "").lower()
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Case {case.get('id', '<unknown>')} has invalid review status: {status!r}")
    return status


def is_runnable(case: dict[str, Any]) -> bool:
    """Legacy checked-in cases run; reviewed candidates require approval."""
    status = review_status(case)
    return status is None or status == "approved"


def validate_case(case: dict[str, Any], *, require_approved: bool = False) -> None:
    case_id = case.get("id")
    task = case.get("task")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Every eval case needs a non-empty string id")
    if task not in SUPPORTED_TASKS:
        raise ValueError(f"Case {case_id} has unsupported task: {task!r}")

    status = review_status(case)
    if require_approved and status != "approved":
        raise ValueError(f"Case {case_id} is not approved")
    if status == "approved" and not isinstance(case.get("expected"), dict):
        raise ValueError(f"Approved case {case_id} needs an expected object")

    expected = case.get("expected")
    if status == "approved" and isinstance(expected, dict):
        if task == "reconciliation":
            action = str(expected.get("action") or "").upper()
            insight_type = str(expected.get("type") or "").upper()
            if action not in {"MERGE", "REPLACE"}:
                raise ValueError(f"Approved reconciliation case {case_id} needs expected.action")
            if insight_type not in {"COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"}:
                raise ValueError(f"Approved reconciliation case {case_id} needs expected.type")
            if not isinstance(expected.get("required_facts"), list):
                raise ValueError(f"Approved reconciliation case {case_id} needs expected.required_facts")
        elif task == "retrieval":
            relevant_ids = expected.get("relevant_ids")
            if not isinstance(relevant_ids, list) or not relevant_ids:
                raise ValueError(f"Approved retrieval case {case_id} needs expected.relevant_ids")
            if not isinstance(expected.get("forbidden_ids", []), list):
                raise ValueError(f"Approved retrieval case {case_id} expected.forbidden_ids must be a list")
        elif task == "tutor" and not isinstance(expected.get("required_terms", []), list):
            raise ValueError(f"Approved tutor case {case_id} expected.required_terms must be a list")

    if task in {"question", "mcq", "insight", "tutor", "reconciliation"}:
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            raise ValueError(f"Case {case_id} needs a non-empty prompt")
    elif task == "retrieval":
        inputs = case.get("input")
        if not isinstance(inputs, dict) or not str(inputs.get("query") or "").strip():
            raise ValueError(f"Retrieval case {case_id} needs input.query")
        candidates = inputs.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError(f"Retrieval case {case_id} needs input.candidates")
        for candidate in candidates:
            if not isinstance(candidate, dict) or not candidate.get("id") or not candidate.get("content"):
                raise ValueError(f"Retrieval case {case_id} has an invalid candidate")
        candidate_ids = [str(candidate["id"]) for candidate in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"Retrieval case {case_id} has duplicate candidate ids")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            records.append(value)
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    materialized = list(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in materialized:
            handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
    return len(materialized)
