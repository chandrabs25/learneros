# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# HDBSCAN has no Linux wheel for the locked version, so compile it only in the
# disposable builder stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.18@sha256:5713fa8217f92b80223bc83aac7db36ec80a84437dbc0d04bbc659cae030d8c9 /uv /bin/uv
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --gid 10001 learneros \
    && useradd --uid 10001 --gid learneros --no-create-home --home-dir /app learneros

COPY --from=builder --chown=learneros:learneros /app/.venv /app/.venv
COPY --chown=learneros:learneros app ./app

USER learneros

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
