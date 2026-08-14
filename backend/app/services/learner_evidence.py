"""Durable Learner Evidence persistence and Current Learner State convergence.

Routes submit validated evidence through ``queue_learner_evidence``. This module
owns durable claiming, reconciliation, embeddings, graph persistence, retries,
dead letters, cache invalidation, and Assessment Attempt result accounting.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
import time
from typing import Any, Callable
import uuid

from app.assessment_observability import AssessmentStatus, assessment_event, elapsed_ms
from app.config import settings
from app.database import read_query, write_query
from app.services.assessment_attempts import record_assessment_insight_result
from app.services.insight_cache import invalidate_student
from app.services.llm import llm_service


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PersistenceContext:
    assessment_id: str | None = None
    assessment_kind: str = "unknown"
    assessment_started_at: float | None = None
    queued_at: float | None = None
    insight_index: int | None = None
    insight_total: int | None = None
    job_id: str | None = None
    claim_token: str | None = None


@dataclass
class LearnerEvidenceAdapters:
    read: Callable[..., list[dict[str, Any]]]
    write: Callable[..., list[dict[str, Any]]]
    reconcile_text: Callable[[str], str]
    embed: Callable[[str], list[float]]
    invalidate: Callable[[str], None]
    record_result: Callable[..., dict[str, Any] | None]
    emit_event: Callable[..., None] = assessment_event


class LearnerEvidencePersistence:
    """Deep module for turning Learner Evidence into Current Learner State."""

    def __init__(
        self,
        adapters: LearnerEvidenceAdapters,
        *,
        event_logger: logging.Logger = logger,
        retry_limit: int = 2,
    ) -> None:
        self.adapters = adapters
        self.event_logger = event_logger
        self.retry_limit = retry_limit

    def persist(
        self,
        student_id: str,
        evidence: dict[str, Any],
        *,
        context: PersistenceContext | None = None,
    ) -> bool:
        """Persist one evidence item without leaking failures into the response path."""
        ctx = context or PersistenceContext()
        persistence_started_at = time.monotonic()
        self._event(
            ctx,
            AssessmentStatus.PERSISTENCE_STARTED,
            stage="queue_wait",
            duration_ms=elapsed_ms(ctx.queued_at) if ctx.queued_at is not None else 0.0,
            result="success",
        )

        last_error_type = "UnknownError"
        attempt_started_at = persistence_started_at
        persistence_succeeded = False
        for attempt in range(1, self.retry_limit + 1):
            attempt_started_at = time.monotonic()
            try:
                self._persist_once(student_id, evidence, ctx)
                self._event(
                    ctx,
                    AssessmentStatus.PERSISTENCE_ATTEMPT_COMPLETED,
                    stage="persistence_attempt",
                    duration_ms=elapsed_ms(attempt_started_at),
                    result="success",
                    attempt=attempt,
                    attempt_limit=self.retry_limit,
                )
                persistence_succeeded = True
                break
            except Exception as exc:
                last_error_type = type(exc).__name__
                if attempt < self.retry_limit:
                    self._event(
                        ctx,
                        AssessmentStatus.PERSISTENCE_RETRY,
                        stage="persistence_attempt",
                        duration_ms=elapsed_ms(attempt_started_at),
                        result="retry",
                        failed_attempt=attempt,
                        next_attempt=attempt + 1,
                        attempt_limit=self.retry_limit,
                        concept_id=evidence.get("concept_id"),
                        source_id=evidence.get("source_id"),
                        error_type=type(exc).__name__,
                    )
                self.event_logger.warning(
                    "Learner Evidence persistence attempt failed",
                    extra={
                        "attempt": attempt,
                        "attempt_limit": self.retry_limit,
                        "error_type": last_error_type,
                    },
                )

        if persistence_succeeded:
            try:
                self.adapters.invalidate(student_id)
            except Exception as exc:
                self.event_logger.warning(
                    "Learner Evidence cache invalidation failed",
                    extra={"error_type": type(exc).__name__},
                )
            if not self._prepare_job_outcome(ctx, success=True):
                return False
            aggregate = self._safe_record_outcome(ctx, success=True)
            self._complete(
                ctx,
                persistence_started_at,
                result="success",
                aggregate=aggregate,
            )
            return aggregate is not None or ctx.assessment_id is None

        self._event(
            ctx,
            AssessmentStatus.PERSISTENCE_FAILED,
            stage="persistence_attempt",
            duration_ms=elapsed_ms(attempt_started_at),
            result="failure",
            concept_id=evidence.get("concept_id"),
            source_id=evidence.get("source_id"),
        )
        dead_letter_recorded = self._record_failure(
            student_id, evidence, last_error_type, ctx
        )
        if ctx.job_id and not dead_letter_recorded:
            return False
        if not self._prepare_job_outcome(
            ctx,
            success=False,
            error_type=last_error_type,
        ):
            return False
        aggregate = self._safe_record_outcome(
            ctx, success=False, error_type=last_error_type
        )
        self._complete(
            ctx,
            persistence_started_at,
            result="failure",
            aggregate=aggregate,
        )
        return False

    def _prepare_job_outcome(
        self,
        ctx: PersistenceContext,
        *,
        success: bool,
        error_type: str | None = None,
    ) -> bool:
        try:
            self._mark_job_ready(ctx, success=success, error_type=error_type)
            return True
        except Exception as exc:
            self._accounting_deferred(ctx, exc, stage="job_state")
            return False

    def _safe_record_outcome(
        self,
        ctx: PersistenceContext,
        *,
        success: bool,
        error_type: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            aggregate = self._record_outcome(
                ctx, success=success, error_type=error_type
            )
        except Exception as exc:
            self._accounting_deferred(ctx, exc, stage="attempt_accounting")
            return None
        if ctx.assessment_id and aggregate is None:
            self._accounting_deferred(
                ctx, RuntimeError("assessment_attempt_not_updated"), stage="attempt_accounting"
            )
        return aggregate

    def _accounting_deferred(
        self,
        ctx: PersistenceContext,
        exc: Exception,
        *,
        stage: str,
    ) -> bool:
        self._event(
            ctx,
            AssessmentStatus.INVARIANT_FAILED,
            stage=stage,
            duration_ms=0.0,
            result="failure",
            reason="assessment_accounting_deferred",
            error_type=type(exc).__name__,
        )
        self.event_logger.warning(
            "Learner Evidence accounting deferred for recovery",
            extra={"stage": stage, "error_type": type(exc).__name__},
        )

    def _persist_once(
        self,
        student_id: str,
        evidence: dict[str, Any],
        ctx: PersistenceContext,
    ) -> None:
        concept_id = evidence.get("concept_id", "")
        insight_id = f"insight:{ctx.job_id}" if ctx.job_id else f"insight:{uuid.uuid4().hex}"
        if not concept_id:
            evidence["persisted"] = False
            self._event(
                ctx,
                AssessmentStatus.INVARIANT_FAILED,
                stage="precondition",
                duration_ms=0.0,
                result="failure",
                reason="missing_concept_id",
            )
            raise ValueError("Cannot persist Learner Evidence without concept_id")

        db_read_started_at = time.monotonic()
        old_rows = self.adapters.read(
            """
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true, category: $category})
                  -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
            WHERE i.id <> $insight_id AND (i)-[:ABOUT_SOURCE]->({id: $source_id})
            RETURN i.id AS id, i.type AS type, i.content AS content, i.created_at AS created_at
            ORDER BY i.created_at DESC
            """,
            _query_name="insight.lookup_active",
            student_id=student_id,
            concept_id=concept_id,
            source_id=evidence["source_id"],
            category=evidence["category"],
            insight_id=insight_id,
        )
        self._event(
            ctx,
            AssessmentStatus.DB_READ_COMPLETED,
            stage="db_read",
            duration_ms=elapsed_ms(db_read_started_at),
            result="success",
            prior_active_count=len(old_rows),
        )

        reconciliation_started_at = time.monotonic()
        reconciled = self._reconcile(
            old_rows,
            new_type=evidence["type"],
            new_content=evidence["content"],
        )
        evidence["type"] = reconciled["type"]
        evidence["content"] = reconciled["content"]
        self._event(
            ctx,
            AssessmentStatus.RECONCILED,
            stage="reconciliation",
            duration_ms=elapsed_ms(reconciliation_started_at),
            result="success",
            concept_id=concept_id,
            source_id=evidence.get("source_id"),
            prior_active_count=len(old_rows),
            reconcile_action=reconciled.get("action", "NEW"),
            reconciled_type=evidence["type"],
        )

        embedding_started_at = time.monotonic()
        evidence["embedding"] = self.adapters.embed(evidence["content"])
        self._event(
            ctx,
            AssessmentStatus.EMBEDDED,
            stage="embedding",
            duration_ms=elapsed_ms(embedding_started_at),
            result="success",
            model=settings.FIREWORKS_EMBEDDING_MODEL,
            concept_id=concept_id,
            embedding_dimensions=len(evidence["embedding"]),
            embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
        )

        db_write_started_at = time.monotonic()
        try:
            rows = self.adapters.write(
                """
                MATCH (s:Student {id: $student_id})
                MATCH (source {id: $source_id})
                MATCH (concept:Concept {id: $concept_id})
                OPTIONAL MATCH (claimed_job:LearnerEvidenceJob {id: $job_id})
                FOREACH (_ IN CASE WHEN claimed_job IS NULL THEN [] ELSE [1] END |
                    SET claimed_job.fence_revision = coalesce(claimed_job.fence_revision, 0) + 1)
                WITH s, source, concept, claimed_job
                WHERE $job_id IS NULL OR claimed_job.claim_token = $claim_token
                OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(old:Insight {is_active: true, category: $category})
                              -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
                WHERE old.id <> $insight_id AND (old)-[:ABOUT_SOURCE]->({id: $source_id})
                SET old.is_active = false
                WITH s, source, concept, claimed_job, collect(old) AS old_insights
                OPTIONAL MATCH (attempt:AssessmentAttempt {id: $assessment_id})
                WITH s, source, concept, claimed_job, old_insights, attempt
                MERGE (new:Insight {id: $insight_id})
                SET new.assessment_id = $assessment_id, new.type = $type,
                    new.category = $category, new.content = $content,
                    new.embedding = $embedding,
                    new.embedding_model = $embedding_model,
                    new.is_active = true,
                    new.created_at = coalesce(new.created_at, datetime())
                MERGE (s)-[:HAS_INSIGHT]->(new)
                MERGE (new)-[:ABOUT_SOURCE]->(source)
                MERGE (new)-[:ABOUT_CONCEPT]->(concept)
                FOREACH (_ IN CASE WHEN attempt IS NULL THEN [] ELSE [1] END |
                    MERGE (attempt)-[:PRODUCED]->(new))
                FOREACH (old IN old_insights | MERGE (new)-[:SUPERSEDES]->(old))
                WITH s, new, claimed_job
                OPTIONAL MATCH (s)-[:HAS_INSIGHT]->(other:Insight {is_active: true, category: $category})
                               -[:ABOUT_CONCEPT]->(:Concept {id: $concept_id})
                WHERE other.id <> new.id AND (other)-[:ABOUT_SOURCE]->({id: $source_id})
                WITH new, claimed_job,
                     [candidate IN collect(other) WHERE candidate IS NOT NULL] AS competing_insights
                FOREACH (other IN competing_insights | SET other.is_active = false)
                FOREACH (_ IN CASE WHEN claimed_job IS NULL THEN [] ELSE [1] END |
                    SET claimed_job.status = 'PERSISTED', claimed_job.success = true,
                        claimed_job.error_type = null, claimed_job.updated_at = datetime())
                RETURN new.id AS id
                """,
                _query_name="insight.persist",
                student_id=student_id,
                insight_id=insight_id,
                assessment_id=ctx.assessment_id,
                type=evidence["type"],
                category=evidence["category"],
                content=evidence["content"],
                embedding=evidence["embedding"],
                embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
                source_id=evidence["source_id"],
                concept_id=concept_id,
                job_id=ctx.job_id,
                claim_token=ctx.claim_token,
            )
        except Exception as exc:
            self._event(
                ctx,
                AssessmentStatus.INVARIANT_FAILED,
                stage="db_write",
                duration_ms=elapsed_ms(db_write_started_at),
                result="failure",
                reason="database_write_failed",
                error_type=type(exc).__name__,
                concept_id=concept_id,
            )
            raise

        evidence["persisted"] = bool(rows)
        if not rows:
            self._event(
                ctx,
                AssessmentStatus.INVARIANT_FAILED,
                stage="db_write",
                duration_ms=elapsed_ms(db_write_started_at),
                result="failure",
                reason="insight_create_returned_no_rows",
                concept_id=concept_id,
            )
            raise RuntimeError("Learner Evidence write completed without creating a record")
        self._event(
            ctx,
            AssessmentStatus.PERSISTED,
            stage="db_write",
            duration_ms=elapsed_ms(db_write_started_at),
            result="success",
            concept_id=concept_id,
            source_id=evidence.get("source_id"),
            insight_id=rows[0].get("id"),
        )

    def _reconcile(
        self,
        old_evidence: list[dict[str, Any]],
        *,
        new_type: str,
        new_content: str,
    ) -> dict[str, str]:
        if not old_evidence:
            return {"action": "NEW", "type": new_type, "content": new_content}
        old_block = "\n".join(
            f'  - type: {row.get("type", "")}, content: "{(row.get("content") or "").strip()}"'
            for row in old_evidence
        )
        prompt = f"""Respond in STRICT JSON with exactly this schema:
{{
  "action": "REPLACE or MERGE",
  "type": "COMPETENCY or PARTIAL_UNDERSTANDING or MISCONCEPTION",
  "content": "Reconciled insight text"
}}

You have multiple active learning insights about the SAME concept/source for the SAME student.

EXISTING ACTIVE INSIGHTS (most recent first):
{old_block}

NEW INSIGHT (from the current assessment):
  type: {new_type}
  content: "{new_content}"

Use REPLACE for contradiction and MERGE for compatible evidence. Preserve valid
evidence, and choose the final type from COMPETENCY, PARTIAL_UNDERSTANDING, or
MISCONCEPTION according to the unresolved understanding level.
"""
        try:
            raw = self.adapters.reconcile_text(prompt)
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(raw)
            action = str(result.get("action", "")).upper()
            if action not in ("MERGE", "REPLACE"):
                action = "REPLACE"
            evidence_type = result.get("type", new_type)
            if evidence_type not in (
                "COMPETENCY",
                "PARTIAL_UNDERSTANDING",
                "MISCONCEPTION",
            ):
                evidence_type = new_type
            content = result.get("content", new_content)
            if not isinstance(content, str) or not content.strip():
                content = new_content
            return {"action": action, "type": evidence_type, "content": content}
        except Exception:
            return {"action": "REPLACE", "type": new_type, "content": new_content}

    def _record_failure(
        self,
        student_id: str,
        evidence: dict[str, Any],
        error_type: str,
        ctx: PersistenceContext,
    ) -> bool:
        started_at = time.monotonic()
        try:
            rows = self.adapters.write(
                """
                OPTIONAL MATCH (claimed_job:LearnerEvidenceJob {id: $job_id})
                FOREACH (_ IN CASE WHEN claimed_job IS NULL THEN [] ELSE [1] END |
                    SET claimed_job.fence_revision = coalesce(claimed_job.fence_revision, 0) + 1)
                WITH claimed_job
                WHERE $job_id IS NULL OR claimed_job.claim_token = $claim_token
                CREATE (f:InsightPersistenceFailure {
                    id: $failure_id, assessment_id: $assessment_id,
                    student_id: $student_id, concept_id: $concept_id,
                    source_id: $source_id, category: $category,
                    insight_type: $insight_type, content: $content,
                    error_type: $error_type, created_at: datetime()
                })
                RETURN f.id AS id
                """,
                _query_name="insight.dead_letter",
                failure_id=f"insight_failure:{uuid.uuid4().hex}",
                assessment_id=ctx.assessment_id,
                student_id=student_id,
                concept_id=evidence.get("concept_id"),
                source_id=evidence.get("source_id"),
                category=evidence.get("category"),
                insight_type=evidence.get("type"),
                content=evidence.get("content"),
                error_type=error_type,
                job_id=ctx.job_id,
                claim_token=ctx.claim_token,
            )
            if not rows:
                return False
            self._event(
                ctx,
                AssessmentStatus.DEAD_LETTER_RECORDED,
                stage="dead_letter",
                duration_ms=elapsed_ms(started_at),
                result="success",
            )
            return True
        except Exception as exc:
            self._event(
                ctx,
                AssessmentStatus.INVARIANT_FAILED,
                stage="dead_letter",
                duration_ms=elapsed_ms(started_at),
                result="failure",
                reason="dead_letter_write_failed",
                error_type=type(exc).__name__,
            )
            self.event_logger.warning(
                "Failed to write Learner Evidence dead-letter record",
                extra={"error_type": type(exc).__name__},
            )
            return False

    def _record_outcome(
        self,
        ctx: PersistenceContext,
        *,
        success: bool,
        error_type: str | None = None,
    ) -> dict[str, Any] | None:
        if not ctx.assessment_id:
            return None
        if ctx.job_id:
            rows = self.adapters.write(
                """
                MATCH (j:LearnerEvidenceJob {id: $job_id, claim_token: $claim_token})
                MATCH (a:AssessmentAttempt {id: $assessment_id})-[:HAS_EVIDENCE_JOB]->(j)
                WHERE j.status IN ['PERSISTED', 'FAILED_UNACCOUNTED']
                SET j.status = 'COMPLETED', j.success = $success,
                    j.error_type = $error_type, j.completed_at = datetime(),
                    j.updated_at = datetime(), j.evidence_json = null,
                    a.persisted_insight_count = coalesce(a.persisted_insight_count, 0)
                        + CASE WHEN $success THEN 1 ELSE 0 END,
                    a.failed_insight_count = coalesce(a.failed_insight_count, 0)
                        + CASE WHEN $success THEN 0 ELSE 1 END,
                    a.last_insight_error = CASE WHEN $success THEN a.last_insight_error ELSE $error_type END,
                    a.updated_at = datetime()
                WITH a,
                     coalesce(a.persisted_insight_count, 0) AS persisted,
                     coalesce(a.failed_insight_count, 0) AS failed,
                     coalesce(a.expected_insight_count, 0) AS expected
                SET a.insight_status = CASE
                        WHEN persisted + failed < expected THEN 'PROCESSING'
                        WHEN failed = 0 THEN 'COMPLETED'
                        WHEN persisted = 0 THEN 'FAILED'
                        ELSE 'PARTIAL'
                    END,
                    a.reconciliation_completed_at = CASE
                        WHEN persisted + failed >= expected THEN datetime()
                        ELSE a.reconciliation_completed_at
                    END
                RETURN a.insight_status AS insight_status,
                       persisted AS persisted_insight_count,
                       failed AS failed_insight_count,
                       expected AS expected_insight_count
                """,
                _query_name="learner_evidence.account_job",
                job_id=ctx.job_id,
                claim_token=ctx.claim_token,
                assessment_id=ctx.assessment_id,
                success=success,
                error_type=error_type,
            )
            return rows[0] if rows else None
        return self.adapters.record_result(
            assessment_id=ctx.assessment_id,
            success=success,
            error=error_type,
        )

    def _mark_job_ready(
        self,
        ctx: PersistenceContext,
        *,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        if not ctx.job_id:
            return
        rows = self.adapters.write(
            """
            MATCH (j:LearnerEvidenceJob {id: $job_id, claim_token: $claim_token})
            WHERE j.status <> 'COMPLETED'
            SET j.status = CASE WHEN $success THEN 'PERSISTED' ELSE 'FAILED_UNACCOUNTED' END,
                j.success = $success,
                j.error_type = $error_type,
                j.updated_at = datetime()
            RETURN j.id AS id
            """,
            _query_name="learner_evidence.mark_job_ready",
            job_id=ctx.job_id,
            claim_token=ctx.claim_token,
            success=success,
            error_type=error_type,
        )
        if not rows:
            raise RuntimeError("learner_evidence_job_state_update_failed")

    def _event(
        self,
        ctx: PersistenceContext,
        status: AssessmentStatus,
        **fields: Any,
    ) -> None:
        if not ctx.assessment_id:
            return
        self.adapters.emit_event(
            self.event_logger,
            ctx.assessment_id,
            status,
            assessment_kind=ctx.assessment_kind,
            insight_index=ctx.insight_index,
            insight_total=ctx.insight_total,
            **fields,
        )

    def _complete(
        self,
        ctx: PersistenceContext,
        started_at: float,
        *,
        result: str,
        aggregate: dict[str, Any] | None,
    ) -> None:
        self._event(
            ctx,
            AssessmentStatus.PERSISTENCE_COMPLETED,
            stage="persistence_total",
            duration_ms=elapsed_ms(started_at),
            result=result,
        )
        aggregate_status = str((aggregate or {}).get("insight_status") or "")
        if aggregate_status in {"COMPLETED", "PARTIAL", "FAILED"}:
            self._event(
                ctx,
                AssessmentStatus.ASSESSMENT_COMPLETED,
                stage="assessment_total",
                duration_ms=(
                    elapsed_ms(ctx.assessment_started_at)
                    if ctx.assessment_started_at is not None
                    else elapsed_ms(started_at)
                ),
                result="success" if aggregate_status == "COMPLETED" else "failure",
                insight_status=aggregate_status,
            )


def _reconcile_text(prompt: str) -> str:
    return llm_service.generate_text(
        provider="fireworks",
        model=settings.FIREWORKS_MODEL,
        prompt=prompt,
        system="Return only valid JSON matching the requested schema.",
        temperature=0.1,
        json_mode=True,
        timeout=60,
        operation="insight_reconciliation",
    )


def _embed(text: str) -> list[float]:
    return llm_service.embed(
        provider="fireworks",
        model=settings.FIREWORKS_EMBEDDING_MODEL,
        text=text,
        retries=2,
        operation="insight_embedding",
    )


learner_evidence_persistence = LearnerEvidencePersistence(
    LearnerEvidenceAdapters(
        read=read_query,
        write=write_query,
        reconcile_text=_reconcile_text,
        embed=_embed,
        invalidate=invalidate_student,
        record_result=record_assessment_insight_result,
    )
)


def queue_learner_evidence(
    student_id: str,
    evidence_items: list[dict[str, Any]],
    *,
    assessment_id: str,
    assessment_kind: str,
    assessment_started_at: float | None = None,
    schedule: Callable[..., Any],
) -> bool:
    """Transactionally create recoverable jobs, then request immediate processing."""
    if not evidence_items:
        return False
    queued_epoch_ms = round(time.time() * 1000)
    assessment_started_epoch_ms = (
        round((time.time() - (time.monotonic() - assessment_started_at)) * 1000)
        if assessment_started_at is not None
        else queued_epoch_ms
    )
    jobs = [
        {
            "id": f"evidence_job:{uuid.uuid4().hex}",
            "evidence_json": json.dumps(item, separators=(",", ":"), ensure_ascii=True),
            "insight_index": index,
        }
        for index, item in enumerate(evidence_items, start=1)
    ]
    rows = learner_evidence_persistence.adapters.write(
        """
        MATCH (s:Student {id: $student_id})-[:SUBMITTED]->(a:AssessmentAttempt {id: $assessment_id})
        SET a.insight_status = 'QUEUED',
            a.expected_insight_count = size($jobs),
            a.persisted_insight_count = 0,
            a.failed_insight_count = 0,
            a.insights_queued_at = datetime(),
            a.updated_at = datetime()
        WITH a
        UNWIND $jobs AS job
        CREATE (j:LearnerEvidenceJob {
            id: job.id, assessment_id: $assessment_id,
            assessment_kind: $assessment_kind,
            student_id: $student_id, evidence_json: job.evidence_json,
            insight_index: job.insight_index, insight_total: size($jobs),
            status: 'QUEUED', attempts: 0,
            queued_epoch_ms: $queued_epoch_ms,
            assessment_started_epoch_ms: $assessment_started_epoch_ms,
            created_at: datetime(), updated_at: datetime()
        })
        MERGE (a)-[:HAS_EVIDENCE_JOB]->(j)
        RETURN collect(j.id) AS job_ids
        """,
        _query_name="learner_evidence.queue_jobs",
        student_id=student_id,
        assessment_id=assessment_id,
        assessment_kind=assessment_kind,
        queued_epoch_ms=queued_epoch_ms,
        assessment_started_epoch_ms=assessment_started_epoch_ms,
        jobs=jobs,
    )
    if not rows or not rows[0].get("job_ids"):
        return False
    for job_id in rows[0]["job_ids"]:
        schedule(process_learner_evidence_job, job_id)
    return True


def skip_learner_evidence(*, assessment_id: str, reason: str) -> bool:
    """Record a terminal no-persistence decision behind the deep-module seam."""
    rows = learner_evidence_persistence.adapters.write(
        """
        MATCH (a:AssessmentAttempt {id: $assessment_id})
        SET a.insight_status = 'SKIPPED',
            a.insight_skip_reason = $reason,
            a.expected_insight_count = 0,
            a.reconciliation_completed_at = datetime(),
            a.updated_at = datetime()
        RETURN a.id AS id
        """,
        _query_name="learner_evidence.skip",
        assessment_id=assessment_id,
        reason=reason,
    )
    return bool(rows)


def process_learner_evidence_job(job_id: str) -> bool:
    """Claim and process one job; persisted-but-unaccounted jobs only reconcile status."""
    claim_token = uuid.uuid4().hex
    rows = learner_evidence_persistence.adapters.write(
        """
        MATCH (j:LearnerEvidenceJob {id: $job_id})
        SET j.claim_revision = coalesce(j.claim_revision, 0) + 1
        WITH j, j.status AS prior_status
        WHERE j.status IN ['QUEUED', 'PERSISTED', 'FAILED_UNACCOUNTED']
           OR (j.status = 'PROCESSING' AND j.lease_expires_at < datetime())
        SET j.status = CASE
                WHEN prior_status IN ['PERSISTED', 'FAILED_UNACCOUNTED'] THEN prior_status
                ELSE 'PROCESSING'
            END,
            j.claim_token = $claim_token,
            j.lease_expires_at = datetime() + duration('PT3M'),
            j.attempts = coalesce(j.attempts, 0) + 1,
            j.updated_at = datetime()
        RETURN j.id AS job_id, j.assessment_id AS assessment_id,
               j.assessment_kind AS assessment_kind, j.student_id AS student_id,
               j.evidence_json AS evidence_json, j.insight_index AS insight_index,
               j.insight_total AS insight_total, prior_status,
               j.success AS success, j.error_type AS error_type,
               j.queued_epoch_ms AS queued_epoch_ms,
               j.assessment_started_epoch_ms AS assessment_started_epoch_ms
        """,
        _query_name="learner_evidence.claim_job",
        job_id=job_id,
        claim_token=claim_token,
    )
    if not rows:
        return False
    job = rows[0]
    now_epoch_ms = time.time() * 1000
    now_monotonic = time.monotonic()
    queued_epoch_ms = float(job.get("queued_epoch_ms") or now_epoch_ms)
    assessment_started_epoch_ms = float(
        job.get("assessment_started_epoch_ms") or queued_epoch_ms
    )
    context = PersistenceContext(
        assessment_id=job.get("assessment_id"),
        assessment_kind=job.get("assessment_kind") or "unknown",
        insight_index=job.get("insight_index"),
        insight_total=job.get("insight_total"),
        job_id=job_id,
        claim_token=claim_token,
        queued_at=now_monotonic - max(0.0, (now_epoch_ms - queued_epoch_ms) / 1000),
        assessment_started_at=(
            now_monotonic
            - max(0.0, (now_epoch_ms - assessment_started_epoch_ms) / 1000)
        ),
    )
    if job.get("prior_status") in {"PERSISTED", "FAILED_UNACCOUNTED"}:
        success = bool(job.get("success"))
        aggregate = learner_evidence_persistence._safe_record_outcome(
            context,
            success=success,
            error_type=job.get("error_type"),
        )
        return aggregate is not None
    try:
        evidence = json.loads(job.get("evidence_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        evidence = {}
    return learner_evidence_persistence.persist(job["student_id"], evidence, context=context)


def recover_pending_learner_evidence_jobs(
    *,
    limit: int = 10,
    stop_requested: Callable[[], bool] | None = None,
) -> int:
    """Recover queued, unaccounted, or abandoned jobs across process restarts."""
    rows = learner_evidence_persistence.adapters.read(
        """
        MATCH (j:LearnerEvidenceJob)
        WHERE j.status IN ['QUEUED', 'PERSISTED', 'FAILED_UNACCOUNTED']
           OR (j.status = 'PROCESSING' AND j.lease_expires_at < datetime())
        RETURN j.id AS job_id
        ORDER BY j.created_at
        LIMIT $limit
        """,
        _query_name="learner_evidence.recover_jobs",
        limit=max(1, min(limit, 500)),
    )
    completed = 0
    for row in rows:
        if stop_requested and stop_requested():
            break
        if process_learner_evidence_job(row["job_id"]):
            completed += 1
    return completed


async def run_learner_evidence_recovery(
    stop_event: asyncio.Event,
    *,
    interval_seconds: float = 15.0,
) -> None:
    """Continuously recover durable jobs without blocking the event loop."""
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(
                recover_pending_learner_evidence_jobs,
                stop_requested=stop_event.is_set,
            )
        except Exception as exc:
            logger.warning(
                "Learner Evidence recovery pass failed",
                extra={"error_type": type(exc).__name__},
            )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue


def _persist_learner_evidence(
    student_id: str,
    evidence: dict[str, Any],
    *,
    assessment_id: str | None = None,
    assessment_kind: str = "unknown",
    assessment_started_at: float | None = None,
    queued_at: float | None = None,
    insight_index: int | None = None,
    insight_total: int | None = None,
) -> bool:
    """Internal direct persistence seam used by focused module tests."""
    return learner_evidence_persistence.persist(
        student_id,
        evidence,
        context=PersistenceContext(
            assessment_id=assessment_id,
            assessment_kind=assessment_kind,
            assessment_started_at=assessment_started_at,
            queued_at=queued_at,
            insight_index=insight_index,
            insight_total=insight_total,
        ),
    )
