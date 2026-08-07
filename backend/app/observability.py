"""Small, dependency-free request tracing helpers for application logs."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any


_request_id: ContextVar[str] = ContextVar("request_id", default="")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def new_request_id(incoming: str | None = None) -> str:
    """Reuse a safe caller-provided ID or issue a fresh opaque identifier."""
    if incoming and _SAFE_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


def set_request_id(request_id: str):
    return _request_id.set(request_id)


def reset_request_id(token: Any) -> None:
    _request_id.reset(token)


def get_request_id() -> str:
    return _request_id.get()


def fingerprint(value: str) -> str:
    """Return a non-reversible identifier for prompts, responses, or cache keys."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def trace_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a single JSON log line suitable for Fly log search."""
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "request_id": get_request_id() or None,
        **fields,
    }
    logger.info(json.dumps(payload, default=str, separators=(",", ":")))


def trace_exception(logger: logging.Logger, event: str, exc: Exception, **fields: Any) -> None:
    """Emit structured error details while retaining the full traceback in Fly logs."""
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "request_id": get_request_id() or None,
        "error_type": type(exc).__name__,
        "error_message": str(exc)[:500],
        **fields,
    }
    logger.error(json.dumps(payload, default=str, separators=(",", ":")), exc_info=True)
