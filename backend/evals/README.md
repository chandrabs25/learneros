# LearnerOS model evaluations

LearnerOS does not depend on a public benchmark pretending to represent its
student model. The checked-in `core.jsonl` suite is deliberately small,
human-authored, and curriculum-grounded. Private production data can produce
candidate cases, but it does not become evaluation ground truth until a human
reviews the input, expected behavior, and privacy risk.

The runner exercises the same `LLMService` used by the API. It supports
`question`, `mcq`, `insight`, `tutor`, `reconciliation`, and `retrieval` tasks.
It can score checked-in responses without API credentials or call a configured
provider for an online regression run.

## Offline smoke test

```bash
uv run python -m evals.run \
  --responses evals/fixtures/smoke_responses.jsonl \
  --output evals/reports/offline-smoke.json
```

Run the reviewed core suite, including reconciliation and retrieval:

```bash
uv run python -m evals.run \
  --dataset evals/datasets/core.jsonl \
  --responses evals/fixtures/core_responses.jsonl \
  --output evals/reports/offline-core.json
```

## Online provider test

```bash
uv run python -m evals.run \
  --provider fireworks \
  --model accounts/fireworks/models/minimax-m3 \
  --output evals/reports/fireworks.json
```

The command exits non-zero when any case falls below `--case-threshold` or the
overall score falls below `--minimum-score`, so it can be used as a CI quality
gate. Cases carrying a review status run only when `review.status` is
`approved`; legacy checked-in cases without review metadata remain runnable.

## Build a private representative dataset

Export anonymized candidate cases from Neo4j into the gitignored private area:

```bash
uv run python -m evals.export_candidates \
  --output evals/private/candidates.jsonl
```

Tutor conversations are excluded by default because they may contain free-text
personal information. Include them only in a controlled environment:

```bash
uv run python -m evals.export_candidates \
  --include-conversations \
  --output evals/private/candidates.jsonl
```

The exporter removes direct email, phone, and URL identifiers and never writes
student IDs. This is a safety baseline, not proof of anonymity: a human must
still inspect conversation-derived candidates for indirect identifiers.

Each candidate starts as `review.status=pending`. A reviewer must:

1. Confirm the input represents a real product behavior worth protecting.
2. Replace any private or ambiguous text.
3. Fill an explicit `expected` object rather than accepting the historical
   model output as truth.
4. Mark invalid examples `rejected`, or set `review.status=approved` with a
   reviewer identifier.

Promote only validated approved records into a golden dataset:

```bash
uv run python -m evals.promote \
  --input evals/private/candidates.jsonl \
  --output evals/datasets/internal-golden.jsonl
```

Promotion refuses incomplete approved reconciliation/retrieval labels and
removes private candidate outputs and review-only fields. Keep
`internal-golden.jsonl` private if its reviewed inputs still contain student
content; the filename shown above is only an example workflow.

## Task-specific expectations

- `insight`: allowed `concept_ids` and `minimum_insights`.
- `reconciliation`: exact `action` (`MERGE`/`REPLACE`), resulting `type`, facts
  that must survive, and facts that must disappear.
- `retrieval`: relevant IDs, forbidden distractors, minimum recall, and maximum
  result count.
- `tutor`: required pedagogical terms. Human rubric grading can be added later
  for correctness, adaptation, and refusal quality.

Historical reconciled insights do not contain the original incoming evidence or
the model's original action decision, so they are exported only as pending
reconstruction candidates. Likewise, historical tutor turns do not persist the
matched insight IDs from that turn; retrieval labels must be added by a reviewer
rather than inferred from the final answer.

The generated files under `evals/private/` and reports under `evals/reports/`
are gitignored.

## OpenTelemetry / Phoenix

Set the following variables to send FastAPI, model, and eval spans to any
OTLP/HTTP collector:

```dotenv
OTEL_ENABLED=true
OTEL_SERVICE_NAME=learneros-backend
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector.example/v1/traces
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer%20your-api-key
OTEL_SAMPLE_RATIO=1.0
OTEL_CAPTURE_CONTENT=false
```

Prompt and response bodies are hidden by default. LearnerOS custom spans and
logs contain fingerprints, sizes, latency, provider, model, token usage, and
request IDs instead of student content. Enable content capture only in a
controlled development environment.
