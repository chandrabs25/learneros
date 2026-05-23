from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from app.config import settings
from app.database import read_query, write_query
from app.services.teacher_analytics import TYPE_EMBED_WEIGHTS, recency_multiplier


@dataclass(frozen=True)
class StudentEmbedding:
    embedding: list[float]
    source_count: int
    norm: float


def _vector_norm(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def normalize_vector(vec: list[float]) -> list[float]:
    norm = _vector_norm(vec)
    if norm <= 1e-12:
        return vec[:]
    return [v / norm for v in vec]


def _coerce_vector(value: Any) -> list[float] | None:
    if not isinstance(value, list) or not value:
        return None
    try:
        return [float(v) for v in value]
    except Exception:
        return None


def coerce_embedding(value: Any, *, min_vector_norm: float = 0.0) -> tuple[list[float], float] | None:
    vec = _coerce_vector(value)
    if vec is None:
        return None
    norm = _vector_norm(vec)
    if norm < min_vector_norm:
        return None
    return normalize_vector(vec), norm


def build_student_embedding(
    insights: list[dict[str, Any]],
    *,
    min_vector_norm: float = 0.0,
) -> StudentEmbedding | None:
    weighted: list[tuple[list[float], float]] = []
    for ins in insights:
        vec = _coerce_vector(ins.get("embedding"))
        if vec is None:
            continue
        insight_type = str(ins.get("type") or "").upper()
        type_weight = float(TYPE_EMBED_WEIGHTS.get(insight_type, 0.0))
        if type_weight <= 0.0:
            continue
        recency_weight = float(recency_multiplier(ins.get("created_at")))
        weight = type_weight * recency_weight
        if weight <= 0.0:
            continue
        weighted.append((vec, weight))

    if not weighted:
        return None

    dim = len(weighted[0][0])
    acc = [0.0] * dim
    total_weight = 0.0
    source_count = 0
    for vec, weight in weighted:
        if len(vec) != dim:
            continue
        source_count += 1
        total_weight += weight
        for i in range(dim):
            acc[i] += vec[i] * weight

    if total_weight <= 1e-12 or source_count <= 0:
        return None

    mean_vec = [v / total_weight for v in acc]
    norm = _vector_norm(mean_vec)
    if norm < min_vector_norm:
        return None

    return StudentEmbedding(
        embedding=normalize_vector(mean_vec),
        source_count=source_count,
        norm=norm,
    )


def fetch_active_insight_embeddings(student_id: str) -> list[dict[str, Any]]:
    return read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE i.embedding IS NOT NULL
        RETURN i.id AS insight_id,
               i.type AS type,
               i.created_at AS created_at,
               i.embedding AS embedding
        ORDER BY i.created_at DESC
        """,
        student_id=student_id,
    )


def save_student_embedding(student_id: str, built: StudentEmbedding | None) -> None:
    if built is None:
        write_query(
            """
            MATCH (s:Student {id: $student_id})
            REMOVE s.embedding,
                   s.embedding_model,
                   s.embedding_norm
            SET s.embedding_source_count = 0,
                s.embedding_updated_at = datetime()
            """,
            student_id=student_id,
        )
        return

    write_query(
        """
        MATCH (s:Student {id: $student_id})
        SET s.embedding = $embedding,
            s.embedding_model = $embedding_model,
            s.embedding_source_count = $source_count,
            s.embedding_norm = $embedding_norm,
            s.embedding_updated_at = datetime()
        """,
        student_id=student_id,
        embedding=built.embedding,
        embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
        source_count=built.source_count,
        embedding_norm=built.norm,
    )


def update_student_embedding(student_id: str, *, min_vector_norm: float = 0.0) -> StudentEmbedding | None:
    built = build_student_embedding(
        fetch_active_insight_embeddings(student_id),
        min_vector_norm=min_vector_norm,
    )
    save_student_embedding(student_id, built)
    return built
