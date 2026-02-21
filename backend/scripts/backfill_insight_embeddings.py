"""
Backfill embeddings for existing Insight nodes that are missing vectors.

Usage:
  cd backend
  python -m scripts.backfill_insight_embeddings
  python -m scripts.backfill_insight_embeddings --limit 200 --batch-size 25
"""

import argparse
import os
import sys
import time

from openai import OpenAI

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import read_query, write_query  # noqa: E402


def get_embedding_client() -> OpenAI:
    api_key = settings.FIREWORKS_API_KEY_EMBEDDINGS or settings.FIREWORKS_API_KEY
    if not api_key:
        raise RuntimeError("FIREWORKS_API_KEY_EMBEDDINGS (or FIREWORKS_API_KEY) not configured")
    return OpenAI(api_key=api_key, base_url=settings.FIREWORKS_BASE_URL)


def fetch_missing(limit: int) -> list[dict]:
    return read_query(
        """
        MATCH (i:Insight)
        WHERE i.content IS NOT NULL
          AND trim(i.content) <> ''
          AND (i.embedding IS NULL OR size(i.embedding) = 0)
        RETURN i.id AS id, i.content AS content
        ORDER BY i.created_at ASC
        LIMIT $limit
        """,
        limit=limit,
    )


def save_embedding(insight_id: str, embedding: list[float]) -> None:
    write_query(
        """
        MATCH (i:Insight {id: $insight_id})
        SET i.embedding = $embedding,
            i.embedding_model = $embedding_model,
            i.embedding_created_at = datetime()
        """,
        insight_id=insight_id,
        embedding=embedding,
        embedding_model=settings.FIREWORKS_EMBEDDING_MODEL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill missing insight embeddings")
    parser.add_argument("--limit", type=int, default=1000, help="Max insights to backfill in this run")
    parser.add_argument("--batch-size", type=int, default=20, help="Embedding API batch size")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Sleep between batches to reduce rate pressure")
    args = parser.parse_args()

    client = get_embedding_client()
    rows = fetch_missing(args.limit)
    if not rows:
        print("No missing insight embeddings found.")
        return

    print(f"Backfilling embeddings for {len(rows)} insight(s)")
    done = 0

    for i in range(0, len(rows), args.batch_size):
        batch = rows[i:i + args.batch_size]
        inputs = [r["content"] for r in batch]
        ids = [r["id"] for r in batch]

        resp = client.embeddings.create(
            model=settings.FIREWORKS_EMBEDDING_MODEL,
            input=inputs,
        )

        vectors = [d.embedding for d in resp.data]
        if len(vectors) != len(batch):
            raise RuntimeError("Embedding response size mismatch")

        for insight_id, vec in zip(ids, vectors):
            save_embedding(insight_id, [float(x) for x in vec])
            done += 1

        print(f"  processed {done}/{len(rows)}")
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000)

    print("Backfill complete.")


if __name__ == "__main__":
    main()
