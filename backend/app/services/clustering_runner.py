"""
Clustering runner — core logic for building teacher dashboard student clusters.

This module lives inside ``app.services`` so that it can be imported directly
by the admin API router (uvicorn already has ``app`` on its path).

The CLI script ``scripts/build_teacher_clusters.py`` is a thin wrapper around
the :func:`build_for_institute` and :func:`fetch_institute_ids` functions
exposed here.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import uuid

from app.database import read_query, write_query
from app.services.semantic_clustering import semantic_cluster_students
from app.services.teacher_analytics import (
    compute_risk,
    extract_terms,
    iso_now,
)


# ── Data fetching ─────────────────────────────────────────────────────────


def fetch_institute_ids() -> list[str]:
    rows = read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id IS NOT NULL
          AND trim(s.institute_id) <> ''
          AND coalesce(s.role, 'student') = 'student'
        RETURN DISTINCT s.institute_id AS institute_id
        ORDER BY institute_id
        """
    )
    return [r["institute_id"] for r in rows if r.get("institute_id")]


def fetch_students(institute_id: str) -> list[dict]:
    return read_query(
        """
        MATCH (s:Student)
        WHERE s.institute_id = $institute_id
          AND coalesce(s.role, 'student') = 'student'
        RETURN s.id AS student_id,
               s.name AS student_name,
               s.email AS student_email,
               s.embedding AS student_embedding,
               coalesce(s.embedding_source_count, 0) AS student_embedding_source_count
        ORDER BY coalesce(s.name, s.id) ASC
        """,
        institute_id=institute_id,
    )


def fetch_active_insights(student_ids: list[str]) -> list[dict]:
    if not student_ids:
        return []
    return read_query(
        """
        MATCH (s:Student)-[:HAS_INSIGHT]->(i:Insight {is_active: true})
        WHERE s.id IN $student_ids
          AND i.embedding IS NOT NULL
        OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
        OPTIONAL MATCH p=(i)-[:SUPERSEDES*1..]->(old:Insight {type: 'MISCONCEPTION'})
        WITH s, i, c, src, max(length(p)) AS max_chain
        RETURN s.id AS student_id,
               i.id AS insight_id,
               i.type AS type,
               i.category AS category,
               i.content AS content,
               i.created_at AS created_at,
               i.embedding AS embedding,
               c.id AS concept_id,
               c.name AS concept_name,
               src.id AS source_id,
               src.title AS source_title,
               coalesce(max_chain, 0) AS misconception_history_depth
        ORDER BY i.created_at DESC
        """,
        student_ids=student_ids,
    )


# ── Cluster metadata helpers ──────────────────────────────────────────────


def _risk_band_counts_for_students(
    student_ids: list[str],
    insights_by_student: dict[str, list[dict]],
) -> tuple[dict[str, int], list[float]]:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    scores: list[float] = []
    for sid in student_ids:
        risk = compute_risk(insights_by_student.get(sid, []))
        band = str(risk.get("risk_band") or "LOW")
        if band not in counts:
            counts[band] = 0
        counts[band] += 1
        scores.append(float(risk.get("risk_score") or 0.0))
    return counts, scores


def _top_misconceptions(cluster_insights: list[dict], limit: int = 5) -> list[dict]:
    score = Counter()
    latest: dict[str, dict] = {}
    for ins in cluster_insights:
        if str(ins.get("type") or "").upper() != "MISCONCEPTION":
            continue
        content = (str(ins.get("content") or "").strip())[:320]
        if not content:
            continue
        key = content.lower()
        score[key] += 1
        if key not in latest or str(ins.get("created_at") or "") > str(latest[key].get("created_at") or ""):
            latest[key] = {
                "statement": content,
                "count": 0,
                "concept_id": ins.get("concept_id"),
                "concept_name": ins.get("concept_name"),
                "source_id": ins.get("source_id"),
                "source_title": ins.get("source_title"),
            }

    out: list[dict] = []
    for key, cnt in score.most_common(limit):
        row = latest.get(key, {"statement": key[:320]})
        row["count"] = int(cnt)
        out.append(row)
    return out


def _cluster_label(cluster_insights: list[dict], risk_band_counts: dict[str, int], idx: int, is_noise: bool) -> str:
    if is_noise:
        return f"Unassigned mixed-profile learners (Cluster {idx + 1})"

    concept_counts = Counter((ins.get("concept_name") or ins.get("concept_id") or "General") for ins in cluster_insights)
    dominant_concept = concept_counts.most_common(1)[0][0] if concept_counts else "General"

    misconception_terms = Counter()
    for term in extract_terms((ins.get("content") for ins in cluster_insights if str(ins.get("type") or "").upper() == "MISCONCEPTION"), top_n=6):
        misconception_terms[str(term.get("term") or "")] += int(term.get("count") or 0)
    theme = misconception_terms.most_common(1)[0][0] if misconception_terms else "mixed misconceptions"

    high = int(risk_band_counts.get("HIGH") or 0)
    med = int(risk_band_counts.get("MEDIUM") or 0)
    low = int(risk_band_counts.get("LOW") or 0)
    if high >= max(med, low):
        profile = "high-risk"
    elif low >= max(high, med):
        profile = "mastery-leaning"
    else:
        profile = "developing"

    return f"{dominant_concept} / {theme} ({profile}) (Cluster {idx + 1})"


def _recommended_actions(
    cluster_insights: list[dict],
    risk_band_counts: dict[str, int],
    top_concepts: list[dict],
) -> list[str]:
    high = int(risk_band_counts.get("HIGH") or 0)
    misconception_count = sum(1 for i in cluster_insights if str(i.get("type") or "").upper() == "MISCONCEPTION")
    partial_count = sum(1 for i in cluster_insights if str(i.get("type") or "").upper() == "PARTIAL_UNDERSTANDING")
    concept_names = [str(c.get("name") or c.get("id") or "core concept") for c in top_concepts[:2]]
    concept_text = ", ".join(concept_names) if concept_names else "core concepts"

    actions: list[str] = []
    if high > 0 or misconception_count >= partial_count:
        actions.append(f"Re-teach {concept_text} with misconception-first examples and counterexamples.")
        actions.append("Run a diagnostic quiz before moving to new content.")
    if partial_count > 0:
        actions.append(f"Assign prerequisite review for {concept_text} before the next chapter segment.")
    if not actions:
        actions.append("Give a challenge set to convert partial understanding into durable competency.")
    return actions[:3]


# ── Persistence ───────────────────────────────────────────────────────────


def persist_snapshot(
    institute_id: str,
    *,
    algorithm: str,
    k: int,
    members_by_cluster: dict[int, list[str]],
    per_student_meta: dict[str, dict[str, float | int | None]],
    insights_by_student: dict[str, list[dict]],
    quality: dict[str, float | int],
    eligible_students: int,
    noise_students: int,
    high_risk_count: int = 0,
    medium_risk_count: int = 0,
    low_risk_count: int = 0,
    engine_version: str = "semantic_v2",
) -> str:
    snapshot_id = f"cluster_snapshot:{uuid.uuid4().hex}"
    now = iso_now()
    student_count = sum(len(v) for v in members_by_cluster.values())
    write_query(
        """
        CREATE (snap:StudentClusterSnapshot {
            id: $snapshot_id,
            institute_id: $institute_id,
            run_at: datetime($run_at),
            algorithm: $algorithm,
            k: $k,
            student_count: $student_count,
            eligible_students: $eligible_students,
            noise_students: $noise_students,
            high_risk_count: $high_risk_count,
            medium_risk_count: $medium_risk_count,
            low_risk_count: $low_risk_count,
            quality_json: $quality_json,
            engine_version: $engine_version,
            created_at: datetime()
        })
        """,
        snapshot_id=snapshot_id,
        institute_id=institute_id,
        run_at=now,
        algorithm=algorithm,
        k=k,
        student_count=student_count,
        eligible_students=eligible_students,
        noise_students=noise_students,
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
        quality_json=json.dumps(quality),
        engine_version=engine_version,
    )

    sorted_clusters = sorted(members_by_cluster.items(), key=lambda kv: (kv[0] == -1, -len(kv[1]), kv[0]))
    for display_idx, (cluster_idx, student_ids) in enumerate(sorted_clusters):
        cluster_label = "noise" if int(cluster_idx) == -1 else str(cluster_idx)
        cluster_id = f"cluster:{snapshot_id}:{cluster_label}"
        cluster_insights = []
        concept_counts = Counter()
        for sid in student_ids:
            s_insights = insights_by_student.get(sid, [])
            cluster_insights.extend(s_insights)
            for ins in s_insights:
                cid = ins.get("concept_id")
                if cid:
                    cname = ins.get("concept_name") or cid
                    concept_counts[(cid, cname)] += 1

        top_concepts = [
            {"id": cid, "name": cname, "count": cnt}
            for (cid, cname), cnt in concept_counts.most_common(8)
        ]
        top_terms = extract_terms((ins.get("content") for ins in cluster_insights), top_n=8)
        top_misconceptions = _top_misconceptions(cluster_insights, limit=5)
        risk_band_counts, risk_scores = _risk_band_counts_for_students(student_ids, insights_by_student)
        avg_risk = round((sum(risk_scores) / len(risk_scores)) if risk_scores else 0.0, 3)
        is_noise_cluster = int(cluster_idx) == -1
        label = _cluster_label(cluster_insights, risk_band_counts, display_idx, is_noise_cluster)
        actions = _recommended_actions(cluster_insights, risk_band_counts, top_concepts)

        write_query(
            """
            MATCH (snap:StudentClusterSnapshot {id: $snapshot_id})
            CREATE (c:StudentCluster {
                id: $cluster_id,
                snapshot_id: $snapshot_id,
                institute_id: $institute_id,
                label: $label,
                size: $size,
                avg_risk: $avg_risk,
                is_noise_cluster: $is_noise_cluster,
                top_concepts_json: $top_concepts_json,
                top_terms_json: $top_terms_json,
                top_misconceptions_json: $top_misconceptions_json,
                risk_band_counts_json: $risk_band_counts_json,
                recommended_actions_json: $recommended_actions_json,
                created_at: datetime()
            })
            CREATE (c)-[:IN_SNAPSHOT]->(snap)
            """,
            snapshot_id=snapshot_id,
            cluster_id=cluster_id,
            institute_id=institute_id,
            label=label,
            size=len(student_ids),
            avg_risk=avg_risk,
            is_noise_cluster=is_noise_cluster,
            top_concepts_json=json.dumps(top_concepts),
            top_terms_json=json.dumps(top_terms),
            top_misconceptions_json=json.dumps(top_misconceptions),
            risk_band_counts_json=json.dumps(risk_band_counts),
            recommended_actions_json=json.dumps(actions),
        )

        rel_rows = []
        for sid in student_ids:
            meta = per_student_meta.get(sid) or {}
            rel_rows.append(
                {
                    "student_id": sid,
                    "confidence": meta.get("confidence"),
                    "distance": meta.get("distance"),
                }
            )

        write_query(
            """
            MATCH (c:StudentCluster {id: $cluster_id})
            UNWIND $rel_rows AS row
            MATCH (s:Student {id: row.student_id})
            MERGE (s)-[r:IN_CLUSTER {snapshot_id: $snapshot_id}]->(c)
            SET r.confidence = row.confidence,
                r.distance = row.distance
            """,
            cluster_id=cluster_id,
            snapshot_id=snapshot_id,
            rel_rows=rel_rows,
        )

    return snapshot_id


# ── Main entry point ──────────────────────────────────────────────────────


def build_for_institute(
    institute_id: str,
    *,
    k_override: int | None,
    min_students: int,
    min_insights_per_student: int,
    min_vector_norm: float,
    hdbscan_min_cluster_size: int,
    hdbscan_min_samples: int | None,
) -> dict:
    students = fetch_students(institute_id)
    student_ids = [s["student_id"] for s in students]
    if len(student_ids) < min_students:
        return {
            "institute_id": institute_id,
            "status": "skipped_not_enough_students",
            "student_count": len(student_ids),
            "engine_version": "semantic_v2",
        }

    insights = fetch_active_insights(student_ids)
    insights_by_student: dict[str, list[dict]] = defaultdict(list)
    for ins in insights:
        insights_by_student[ins["student_id"]].append(ins)
    student_embeddings_by_student = {
        s["student_id"]: s["student_embedding"]
        for s in students
        if s.get("student_embedding")
    }
    student_embedding_counts_by_student = {
        s["student_id"]: int(s.get("student_embedding_source_count") or 0)
        for s in students
    }

    cluster_result = semantic_cluster_students(
        ordered_student_ids=student_ids,
        insights_by_student=insights_by_student,
        min_students=min_students,
        min_insights_per_student=min_insights_per_student,
        min_vector_norm=min_vector_norm,
        student_embeddings_by_student=student_embeddings_by_student,
        student_embedding_counts_by_student=student_embedding_counts_by_student,
        k_override=k_override,
        hdbscan_min_cluster_size=hdbscan_min_cluster_size,
        hdbscan_min_samples=hdbscan_min_samples,
    )

    if cluster_result.status != "ok":
        return {
            "institute_id": institute_id,
            "status": cluster_result.status,
            "student_count": len(student_ids),
            "eligible_students": len(cluster_result.eligible_students),
            "errors": cluster_result.errors,
            "engine_version": "semantic_v2",
        }

    noise_students = len(cluster_result.members_by_cluster.get(-1, []))
    all_member_ids = [sid for sids in cluster_result.members_by_cluster.values() for sid in sids]
    agg_risk_counts, _ = _risk_band_counts_for_students(all_member_ids, insights_by_student)
    snapshot_id = persist_snapshot(
        institute_id,
        algorithm=str(cluster_result.algorithm or "kmeans_fallback"),
        k=int(cluster_result.k),
        members_by_cluster=cluster_result.members_by_cluster,
        per_student_meta=cluster_result.per_student_meta,
        insights_by_student=insights_by_student,
        quality=cluster_result.quality,
        eligible_students=len(cluster_result.eligible_students),
        noise_students=noise_students,
        high_risk_count=agg_risk_counts.get("HIGH", 0),
        medium_risk_count=agg_risk_counts.get("MEDIUM", 0),
        low_risk_count=agg_risk_counts.get("LOW", 0),
        engine_version="semantic_v2",
    )
    return {
        "institute_id": institute_id,
        "status": "ok",
        "snapshot_id": snapshot_id,
        "algorithm": cluster_result.algorithm,
        "engine_version": "semantic_v2",
        "student_count": len(student_ids),
        "eligible_students": len(cluster_result.eligible_students),
        "noise_students": noise_students,
        "clusters": len(cluster_result.members_by_cluster),
        "k": cluster_result.k,
        "silhouette": cluster_result.quality.get("silhouette", 0.0),
        "noise_ratio": cluster_result.quality.get("noise_ratio", 0.0),
        "size_imbalance": cluster_result.quality.get("size_imbalance", 0.0),
        "cluster_entropy": cluster_result.quality.get("cluster_entropy", 0.0),
        "errors": cluster_result.errors,
    }
