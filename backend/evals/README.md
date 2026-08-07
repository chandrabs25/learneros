# LearnerOS model evaluations

The evaluation runner exercises the same `LLMService` used by the API. It can
score checked-in responses without API credentials or call a configured model
provider for an online regression run.

## Offline smoke test

```bash
uv run python -m evals.run \
  --responses evals/fixtures/smoke_responses.jsonl \
  --output evals/reports/offline-smoke.json
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
gate. JSONL datasets support `question`, `mcq`, `insight`, and `tutor` tasks.

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
