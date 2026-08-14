# LearnerOS Domain Glossary

## Assessment Submission

A learner's response to one assessment prompt. A submission is one of: a written answer, a selected MCQ option, or a text/image response to an exercise.

## Assessment Execution

The process that evaluates one Assessment Submission against its curriculum source, validates the resulting Learner Evidence, records the assessment outcome, and schedules durable evidence persistence.

## Assessment Attempt

The durable record of one Assessment Execution. It belongs to one learner and tracks evaluation plus the queued, processing, completed, partial, failed, or skipped reconciliation of its Learner Evidence.

## Learner Evidence

A structured observation, grounded in one Assessment Submission and one curriculum source, that describes a competency, partial understanding, or misconception. Learner Evidence is queued and persisted after the learner-facing evaluation. It is historical input to Current Learner State; it is not itself the learner's complete current state.

## Learner Evidence Job

The durable Neo4j work record created before an authenticated assessment reports evidence as queued. A worker acquires a claim token and lease, persists its Learner Evidence with an idempotent insight identity, and atomically accounts the result on the Assessment Attempt. Queued, expired-lease, and persisted-but-unaccounted jobs are recoverable after a process restart.

## Current Learner State

The active, student-specific projection produced by reconciling persisted Learner Evidence for the same curriculum source and concept. It may update after the assessment response because evidence persistence runs outside the learner-facing request path.
