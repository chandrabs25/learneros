# Durable Learner Evidence jobs

Status: Accepted

## Context

Assessment feedback must return before reconciliation, embedding, and insight persistence complete. FastAPI process-local background tasks alone can be lost when a worker restarts, leaving an Assessment Attempt permanently queued. A graph write can also succeed while its attempt-status update fails.

## Decision

Create one Neo4j `LearnerEvidenceJob` per validated evidence item in the same write that marks the Assessment Attempt queued. Process jobs outside the learner response, use a deterministic insight ID derived from the job ID, and atomically mark a job complete while updating aggregate attempt counters. Workers acquire a lock-before-predicate claim token and lease so only the current claimant may mutate a job. A periodic worker reclaims queued, persisted-but-unaccounted, failed-but-unaccounted, and expired-lease processing jobs.

Keep learner-facing correctness synchronous. Export only sanitized failure type/status metadata from the persistence boundary.
Clear the duplicated `evidence_json` job payload atomically at completion. Completed jobs retain only minimal status/provenance; terminal dead-letter records retain the evidence needed for explicit operational recovery.

## Consequences

- A response reports `queued` only after recoverable work exists.
- Restarts and accounting failures converge without requiring the learner to resubmit.
- Deterministic insight IDs make repeated processing idempotent at the graph identity boundary.
- Neo4j now stores short-lived operational job nodes in addition to assessment and learner-state data.
- Deployment must apply the `LearnerEvidenceJob.id` uniqueness constraint and recovery indexes from `backend/scripts/setup_constraints.py`.

## Alternatives considered

- FastAPI `BackgroundTasks` only: rejected because work disappears on process termination.
- A separate queue service: deferred because Neo4j can provide the required transactional boundary with the existing deployment; revisit if throughput or queue isolation requires it.
