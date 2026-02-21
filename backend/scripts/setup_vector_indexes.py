"""
Create Neo4j vector index(es) used by AI Tutor retrieval.

Usage:
  cd backend
  python -m scripts.setup_vector_indexes
  python -m scripts.setup_vector_indexes --dimensions 1024
"""

import argparse
import os
import sys

from openai import OpenAI

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import get_driver  # noqa: E402

INDEX_NAME = "insight_embedding_index"


def get_embedding_client() -> OpenAI:
    api_key = settings.FIREWORKS_API_KEY_EMBEDDINGS or settings.FIREWORKS_API_KEY
    if not api_key:
        raise RuntimeError("FIREWORKS_API_KEY_EMBEDDINGS (or FIREWORKS_API_KEY) not configured")
    return OpenAI(api_key=api_key, base_url=settings.FIREWORKS_BASE_URL)


def infer_dimensions() -> int:
    client = get_embedding_client()
    resp = client.embeddings.create(
        model=settings.FIREWORKS_EMBEDDING_MODEL,
        input="dimension probe",
    )
    vec = resp.data[0].embedding if resp.data else None
    if not vec:
        raise RuntimeError("Could not infer embedding dimensions")
    return len(vec)


def create_index(dimensions: int) -> None:
    driver = get_driver()
    cypher = f"""
    CREATE VECTOR INDEX {INDEX_NAME} IF NOT EXISTS
    FOR (i:Insight) ON (i.embedding)
    OPTIONS {{
      indexConfig: {{
        `vector.dimensions`: {dimensions},
        `vector.similarity_function`: 'cosine'
      }}
    }}
    """
    with driver.session() as session:
        session.run(cypher)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Neo4j vector index for insight embeddings")
    parser.add_argument("--dimensions", type=int, default=0, help="Embedding dimensions (auto-infer when omitted)")
    args = parser.parse_args()

    dims = args.dimensions or infer_dimensions()
    print(f"Using embedding dimensions: {dims}")
    create_index(dims)
    print(f"Created/verified vector index: {INDEX_NAME}")


if __name__ == "__main__":
    main()
