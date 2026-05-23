"""
Create Neo4j vector index(es) used by LearnerOS retrieval.

Usage:
  cd backend
  python -m scripts.setup_vector_indexes
  python -m scripts.setup_vector_indexes --dimensions 4096
"""

import argparse
import os
import sys

from openai import OpenAI

# Allow running from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import get_driver  # noqa: E402

VECTOR_INDEXES = (
    ("insight_embedding_index", "Insight", "i", "embedding"),
    ("student_embedding_index", "Student", "s", "embedding"),
)


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


def create_indexes(dimensions: int) -> None:
    driver = get_driver()
    with driver.session() as session:
        for index_name, label, variable, property_name in VECTOR_INDEXES:
            cypher = f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR ({variable}:{label}) ON ({variable}.{property_name})
            OPTIONS {{
              indexConfig: {{
                `vector.dimensions`: {dimensions},
                `vector.similarity_function`: 'cosine'
              }}
            }}
            """
            session.run(cypher)


def index_names() -> str:
    return ", ".join(index_name for index_name, *_ in VECTOR_INDEXES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Neo4j vector indexes for embeddings")
    parser.add_argument("--dimensions", type=int, default=0, help="Embedding dimensions (auto-infer when omitted)")
    args = parser.parse_args()

    dims = args.dimensions or infer_dimensions()
    print(f"Using embedding dimensions: {dims}")
    create_indexes(dims)
    print(f"Created/verified vector indexes: {index_names()}")


if __name__ == "__main__":
    main()
