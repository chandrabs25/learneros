from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import random
import re
from typing import Iterable


InsightRow = dict

RISK_WEIGHTS = {
    "MISCONCEPTION": 5.0,
    "PARTIAL_UNDERSTANDING": 2.0,
    "COMPETENCY": -2.0,
}

TYPE_EMBED_WEIGHTS = {
    "MISCONCEPTION": 1.0,
    "PARTIAL_UNDERSTANDING": 0.6,
    "COMPETENCY": 0.3,
}

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "about", "when",
    "where", "what", "which", "while", "their", "there", "because", "student",
    "students", "understanding", "concept", "concepts", "shows", "showing", "still",
    "needs", "need", "more", "than", "have", "has", "had", "were", "was", "are",
    "but", "not", "does", "did", "can", "could", "should", "would", "across",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None:
        return datetime.now(timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def age_days(value) -> float:
    dt = _to_datetime(value)
    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds() / 86400.0)


def recency_multiplier(created_at) -> float:
    days = age_days(created_at)
    if days <= 7:
        return 1.25
    if days <= 30:
        return 1.0
    return 0.75


def _risk_band(score: float) -> str:
    if score >= 15:
        return "HIGH"
    if score >= 7:
        return "MEDIUM"
    return "LOW"


def compute_risk(insights: list[InsightRow]) -> dict:
    score = 0.0
    mis_count = 0
    comp_count = 0
    persistent = 0

    for ins in insights:
        itype = str(ins.get("type") or "").upper()
        weight = RISK_WEIGHTS.get(itype, 0.0)
        score += weight * recency_multiplier(ins.get("created_at"))

        if itype == "MISCONCEPTION":
            mis_count += 1
            if int(ins.get("misconception_history_depth") or 0) >= 2:
                persistent += 1
        elif itype == "COMPETENCY":
            comp_count += 1

    if persistent > 0:
        score += 2.0 * persistent

    reasons: list[str] = []
    if mis_count >= 3:
        reasons.append("HIGH_MISCONCEPTION_COUNT")
    if persistent > 0:
        reasons.append("PERSISTENT_MISCONCEPTIONS")
    if comp_count == 0 and mis_count > 0:
        reasons.append("LOW_COMPETENCY_OFFSET")

    return {
        "risk_score": round(score, 2),
        "risk_band": _risk_band(score),
        "reasons": reasons,
    }


def aggregate_student_vector(insights: list[InsightRow]) -> list[float] | None:
    vectors: list[tuple[list[float], float]] = []
    for ins in insights:
        emb = ins.get("embedding")
        if not isinstance(emb, list) or not emb:
            continue
        try:
            vec = [float(v) for v in emb]
        except Exception:
            continue
        w = TYPE_EMBED_WEIGHTS.get(str(ins.get("type") or "").upper(), 0.0)
        if w <= 0:
            continue
        vectors.append((vec, w))

    if not vectors:
        return None
    dim = len(vectors[0][0])
    total_w = sum(w for _, w in vectors)
    if total_w <= 0:
        return None
    acc = [0.0] * dim
    for vec, w in vectors:
        if len(vec) != dim:
            continue
        for i, val in enumerate(vec):
            acc[i] += w * val
    return [x / total_w for x in acc]


def _sqdist(a: list[float], b: list[float]) -> float:
    return sum((x - y) * (x - y) for x, y in zip(a, b))


def kmeans(points: list[list[float]], k: int, seed: int = 42, max_iter: int = 40) -> list[int]:
    if not points:
        return []
    n = len(points)
    if k <= 1 or n == 1:
        return [0] * n
    k = min(k, n)
    rnd = random.Random(seed)

    centroids = [points[i][:] for i in rnd.sample(range(n), k)]
    assignment = [-1] * n

    for _ in range(max_iter):
        changed = False
        for i, p in enumerate(points):
            best_idx = 0
            best_dist = _sqdist(p, centroids[0])
            for c in range(1, k):
                d = _sqdist(p, centroids[c])
                if d < best_dist:
                    best_dist = d
                    best_idx = c
            if assignment[i] != best_idx:
                assignment[i] = best_idx
                changed = True

        if not changed:
            break

        dims = len(points[0])
        sums = [[0.0] * dims for _ in range(k)]
        counts = [0] * k
        for idx, p in zip(assignment, points):
            counts[idx] += 1
            for d in range(dims):
                sums[idx][d] += p[d]

        for c in range(k):
            if counts[c] == 0:
                centroids[c] = points[rnd.randrange(n)][:]
            else:
                centroids[c] = [s / counts[c] for s in sums[c]]

    return assignment


def choose_k(student_count: int) -> int:
    if student_count <= 1:
        return 1
    return min(8, max(2, int(math.floor(math.sqrt(student_count / 2.0)))))


def extract_terms(contents: Iterable[str], top_n: int = 8) -> list[dict]:
    unigram = Counter()
    bigram = Counter()
    for content in contents:
        text = str(content or "").lower()
        words = [w for w in re.findall(r"[a-z]{3,}", text) if w not in STOPWORDS]
        for w in words:
            unigram[w] += 1
        for i in range(len(words) - 1):
            pair = f"{words[i]} {words[i+1]}"
            bigram[pair] += 1

    result: list[dict] = []
    for term, count in bigram.most_common(top_n // 2):
        result.append({"term": term, "count": count, "kind": "bigram"})
    for term, count in unigram.most_common(top_n):
        if len(result) >= top_n:
            break
        result.append({"term": term, "count": count, "kind": "unigram"})
    return result[:top_n]

