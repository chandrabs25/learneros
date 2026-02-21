"""
Observability utilities for optional MLflow prompt tracing.
"""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)
_mlflow_initialized = False


def setup_mlflow_tracing() -> None:
    """Enable MLflow tracing for OpenAI-compatible clients (e.g., Fireworks)."""
    global _mlflow_initialized

    if _mlflow_initialized or not settings.MLFLOW_ENABLE_TRACING:
        return

    try:
        import mlflow
    except Exception as exc:  # pragma: no cover
        logger.warning("MLflow tracing enabled but mlflow import failed: %s", exc)
        return

    try:
        # Use an explicit DB-backed local store by default to avoid path parsing issues.
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI or "sqlite:///mlflow.db")
        if settings.MLFLOW_EXPERIMENT_NAME:
            mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

        mlflow.openai.autolog()
        _mlflow_initialized = True
        logger.info("MLflow OpenAI tracing enabled for Fireworks requests")
    except Exception:  # pragma: no cover
        logger.exception("Failed to initialize MLflow tracing")
