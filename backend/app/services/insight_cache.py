"""Short-lived projections of learner insights shared across assessment routes."""

from __future__ import annotations

import time
from typing import Any


_CACHE_TTL_SECONDS = 20.0
_cache: dict[str, tuple[float, object]] = {}


def get(key: str) -> Any | None:
    row = _cache.get(key)
    if not row:
        return None
    timestamp, payload = row
    if (time.time() - timestamp) > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return payload


def set(key: str, payload: object) -> None:
    _cache[key] = (time.time(), payload)


def invalidate_student(student_id: str) -> None:
    prefixes = (
        f"my_insights|{student_id}|",
        f"subsection_insights|{student_id}|",
        f"prereq_state|{student_id}|",
    )
    for key in list(_cache):
        if key.startswith(prefixes):
            _cache.pop(key, None)
