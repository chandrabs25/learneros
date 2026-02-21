from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Any

from app.services.teacher_analytics import TYPE_EMBED_WEIGHTS, choose_k, kmeans, recency_multiplier


@dataclass
class SemanticClusterResult:
    status: str
    algorithm: str | None
    k: int
    eligible_students: list[str]
    members_by_cluster: dict[int, list[str]]
    per_student_meta: dict[str, dict[str, float | int | None]]
    quality: dict[str, float | int]
    errors: list[str]


def _vector_norm(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def _normalize(vec: list[float]) -> list[float]:
    n = _vector_norm(vec)
    if n <= 1e-12:
        return vec[:]
    return [v / n for v in vec]


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    # vectors are normalized in this pipeline; still clamp for safety
    dot = max(-1.0, min(1.0, dot))
    return 1.0 - dot


def _size_imbalance(sizes: list[int]) -> float:
    non_zero = [s for s in sizes if s > 0]
    if len(non_zero) <= 1:
        return 0.0
    mn = min(non_zero)
    mx = max(non_zero)
    if mn <= 0:
        return float(mx)
    return round(mx / mn, 4)


def _cluster_entropy(sizes: list[int]) -> float:
    non_zero = [s for s in sizes if s > 0]
    total = sum(non_zero)
    if total <= 0 or len(non_zero) <= 1:
        return 0.0
    h = 0.0
    for s in non_zero:
        p = s / total
        h -= p * math.log2(max(p, 1e-12))
    return round(h / math.log2(len(non_zero)), 4)


def _silhouette_cosine(points: list[list[float]], labels: list[int]) -> float:
    # Ignore noise label=-1 for silhouette.
    valid_idx = [i for i, lab in enumerate(labels) if lab != -1]
    if len(valid_idx) < 3:
        return 0.0
    uniq = sorted({labels[i] for i in valid_idx})
    if len(uniq) < 2:
        return 0.0

    by_cluster: dict[int, list[int]] = defaultdict(list)
    for i in valid_idx:
        by_cluster[labels[i]].append(i)

    s_vals: list[float] = []
    for i in valid_idx:
        own = labels[i]
        own_members = by_cluster[own]

        if len(own_members) <= 1:
            a = 0.0
        else:
            a = sum(_cosine_distance(points[i], points[j]) for j in own_members if j != i) / (len(own_members) - 1)

        b = float("inf")
        for other, idxs in by_cluster.items():
            if other == own or not idxs:
                continue
            d = sum(_cosine_distance(points[i], points[j]) for j in idxs) / len(idxs)
            if d < b:
                b = d

        if not math.isfinite(b):
            continue
        denom = max(a, b)
        s = 0.0 if denom <= 1e-12 else (b - a) / denom
        s_vals.append(s)

    if not s_vals:
        return 0.0
    return round(sum(s_vals) / len(s_vals), 4)


def _build_student_vector(
    insights: list[dict[str, Any]],
    *,
    min_vector_norm: float,
) -> tuple[list[float], float] | None:
    weighted: list[tuple[list[float], float]] = []
    for ins in insights:
        emb = ins.get("embedding")
        if not isinstance(emb, list) or not emb:
            continue
        try:
            vec = [float(v) for v in emb]
        except Exception:
            continue
        t = str(ins.get("type") or "").upper()
        type_weight = float(TYPE_EMBED_WEIGHTS.get(t, 0.0))
        if type_weight <= 0.0:
            continue
        rec_weight = float(recency_multiplier(ins.get("created_at")))
        w = type_weight * rec_weight
        if w <= 0.0:
            continue
        weighted.append((vec, w))

    if not weighted:
        return None

    dim = len(weighted[0][0])
    acc = [0.0] * dim
    total_w = 0.0
    for vec, w in weighted:
        if len(vec) != dim:
            continue
        total_w += w
        for i in range(dim):
            acc[i] += vec[i] * w

    if total_w <= 1e-12:
        return None

    mean_vec = [v / total_w for v in acc]
    norm = _vector_norm(mean_vec)
    if norm < min_vector_norm:
        return None

    return _normalize(mean_vec), norm


def _run_hdbscan(points: list[list[float]], *, min_cluster_size: int, min_samples: int | None) -> tuple[list[int], list[float]]:
    import numpy as np  # type: ignore
    import hdbscan  # type: ignore

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        prediction_data=False,
    )
    labels = clusterer.fit_predict(np.asarray(points, dtype=float)).tolist()
    probabilities = (
        [float(p) for p in clusterer.probabilities_.tolist()]
        if getattr(clusterer, "probabilities_", None) is not None
        else [1.0] * len(points)
    )
    return labels, probabilities


def semantic_cluster_students(
    *,
    ordered_student_ids: list[str],
    insights_by_student: dict[str, list[dict[str, Any]]],
    min_students: int,
    min_insights_per_student: int,
    min_vector_norm: float,
    k_override: int | None = None,
    hdbscan_min_cluster_size: int = 4,
    hdbscan_min_samples: int | None = None,
) -> SemanticClusterResult:
    eligible_students: list[str] = []
    vectors: list[list[float]] = []
    errors: list[str] = []

    for sid in ordered_student_ids:
        s_insights = insights_by_student.get(sid, [])
        if len(s_insights) < min_insights_per_student:
            continue
        built = _build_student_vector(s_insights, min_vector_norm=min_vector_norm)
        if built is None:
            continue
        vec, _ = built
        eligible_students.append(sid)
        vectors.append(vec)

    if len(eligible_students) < min_students:
        return SemanticClusterResult(
            status="skipped_not_enough_vectorized_students",
            algorithm=None,
            k=0,
            eligible_students=eligible_students,
            members_by_cluster={},
            per_student_meta={},
            quality={
                "silhouette": 0.0,
                "noise_ratio": 0.0,
                "size_imbalance": 0.0,
                "cluster_entropy": 0.0,
            },
            errors=errors,
        )

    labels: list[int]
    confidence: list[float | None]
    distance: list[float | None]
    algorithm = "hdbscan"

    try:
        labels, probs = _run_hdbscan(
            vectors,
            min_cluster_size=max(2, hdbscan_min_cluster_size),
            min_samples=hdbscan_min_samples,
        )
        confidence = [max(0.0, min(1.0, float(p))) for p in probs]
        distance = [None] * len(labels)
        non_noise = {l for l in labels if l != -1}
        if len(non_noise) < 2:
            raise RuntimeError("HDBSCAN produced <2 non-noise clusters")
    except Exception as exc:
        errors.append(f"hdbscan_failed:{exc}")
        algorithm = "kmeans_fallback"
        k = k_override if (k_override and k_override > 1) else choose_k(len(eligible_students))
        k = min(k, len(eligible_students))
        labels = kmeans(vectors, k=k, seed=42, max_iter=60)
        confidence = [None] * len(labels)

        # Distance-to-centroid for fallback mode.
        by_cluster: dict[int, list[int]] = defaultdict(list)
        for idx, lab in enumerate(labels):
            by_cluster[lab].append(idx)
        centroids: dict[int, list[float]] = {}
        for lab, idxs in by_cluster.items():
            dim = len(vectors[0])
            acc = [0.0] * dim
            for i in idxs:
                for d in range(dim):
                    acc[d] += vectors[i][d]
            centroids[lab] = _normalize([v / max(1, len(idxs)) for v in acc])
        distance = [round(_cosine_distance(vectors[i], centroids[labels[i]]), 6) for i in range(len(labels))]

    members_by_cluster: dict[int, list[str]] = defaultdict(list)
    per_student_meta: dict[str, dict[str, float | int | None]] = {}
    for sid, lab, conf, dist in zip(eligible_students, labels, confidence, distance):
        members_by_cluster[int(lab)].append(sid)
        per_student_meta[sid] = {
            "label": int(lab),
            "confidence": None if conf is None else round(float(conf), 6),
            "distance": None if dist is None else round(float(dist), 6),
        }

    cluster_sizes = [len(v) for _, v in sorted(members_by_cluster.items(), key=lambda kv: kv[0])]
    noise_count = len(members_by_cluster.get(-1, []))
    quality = {
        "silhouette": _silhouette_cosine(vectors, labels),
        "noise_ratio": round(noise_count / max(1, len(eligible_students)), 4),
        "size_imbalance": _size_imbalance(cluster_sizes),
        "cluster_entropy": _cluster_entropy(cluster_sizes),
    }

    non_noise_clusters = [c for c in members_by_cluster.keys() if c != -1]
    k_out = len(non_noise_clusters)

    return SemanticClusterResult(
        status="ok",
        algorithm=algorithm,
        k=k_out,
        eligible_students=eligible_students,
        members_by_cluster=dict(members_by_cluster),
        per_student_meta=per_student_meta,
        quality=quality,
        errors=errors,
    )
