# LearnerOS Agent Guide

This file gives coding agents repository-wide instructions. More specific `AGENTS.md` files, if added later, apply within their own directories.

## Product invariants

- Question generation uses the requested subsection as primary ground truth. The complete parent section may be supplied only as reference context.
- Concepts do not drive question creation. During evaluation, use direct section concepts; when none exist, use chapter concepts as evaluation-only candidates.
- Learner-facing correctness and feedback stay on the response path. Learner Evidence reconciliation, embedding, and persistence run after the response through durable `LearnerEvidenceJob` records; never replace them with process-only background work.
- Current subsection insights must converge across backend workers; do not reintroduce a process-local cache on that projection.
- All text, JSON, tutoring, evaluation, and embedding paths use Fireworks. Image/handwriting evaluation uses the separate Fireworks vision model.
- Telemetry must not export prompt, response, image, learner-answer, or raw LLM exception content.

## Architecture

- `backend/app/services/assessment_execution.py` owns Assessment Execution orchestration.
- `backend/app/services/learner_evidence.py` owns durable job creation/recovery, leased compare-and-set claims, Learner Evidence reconciliation, embeddings, graph persistence, retries, dead letters, cache invalidation, and atomic Assessment Attempt result accounting.
- Routers translate HTTP requests and schedule work; they must not absorb persistence implementation.
- Use the domain terms defined in `CONTEXT.md` rather than inventing synonyms.

## Verification

- Backend: run `./.venv/bin/python -m pytest -q` from `backend/`.
- Frontend: run targeted ESLint for changed source files and `npm run build` from `frontend/`.
- The full frontend lint command currently scans generated `.open-next` output; prefer targeted source linting unless that configuration is changed.
- Preserve unrelated working-tree changes. Do not describe code as deployed without commit, push, and deployment evidence.

## Documentation

- Update `CONTEXT.md` when domain terminology or lifecycle meaning changes.
- Update `backend/docs/LearnerOS_Backend_Architecture.docx` and its contract in `tmp/docs/backend-architecture/artifact.md` when production architecture changes materially.
- Record durable architectural decisions under `docs/adr/`.

## Agent skills

### Issue tracker

Issues are tracked in this repository's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the standard five-role triage vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository with one root glossary and system-wide ADRs. See `docs/agents/domain.md`.
