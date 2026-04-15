"""
Precompute 3D positions for all Concept nodes using TF-IDF + PCA.

No API keys required – uses concept names as descriptive tokens and
builds TF-IDF vectors, then reduces to 3D with PCA and projects onto
a unit sphere. Semantically related concepts (sharing tokens like
"energy", "force", "cell") cluster together naturally.

Usage:
  cd learneros
  uv run --directory backend python -m scripts.build_concept_positions
"""

import argparse
import json
import math
import os
import sys
from collections import Counter

import numpy as np
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import read_query


def tokenize(name: str) -> list[str]:
    """Split concept name into meaningful tokens."""
    # concept names use underscores: "work_energy_theorem"
    tokens = name.lower().replace("concept:", "").split("_")
    # Filter out very short/common tokens
    stop = {"of", "the", "a", "an", "in", "on", "and", "or", "to", "is", "at", "by", "for", "its"}
    return [t for t in tokens if len(t) > 1 and t not in stop]


def build_tfidf(names: list[str]) -> np.ndarray:
    """Build TF-IDF matrix from concept names."""
    # Tokenize all names
    docs = [tokenize(n) for n in names]

    # Build vocabulary
    vocab: dict[str, int] = {}
    df: Counter = Counter()  # document frequency
    for doc in docs:
        unique_tokens = set(doc)
        for token in unique_tokens:
            if token not in vocab:
                vocab[token] = len(vocab)
            df[token] += 1

    n_docs = len(docs)
    n_vocab = len(vocab)

    # Build TF-IDF matrix
    X = np.zeros((n_docs, n_vocab), dtype=np.float64)
    for i, doc in enumerate(docs):
        tf = Counter(doc)
        for token, count in tf.items():
            j = vocab[token]
            # TF * IDF
            X[i, j] = (1 + math.log(count)) * math.log(n_docs / (1 + df[token]))

    # L2 normalize rows
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X = X / norms

    return X


def pca_3d(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """PCA → 3 components. Returns (projected, explained_variance_ratios)."""
    mean = X.mean(axis=0)
    X_c = X - mean

    # Use SVD for numerical stability (better than covariance for wide matrices)
    U, S, Vt = np.linalg.svd(X_c, full_matrices=False)
    components = Vt[:3]  # top 3 right singular vectors

    X_3d = X_c @ components.T

    # Explained variance
    total_var = (S ** 2).sum()
    explained = (S[:3] ** 2) / total_var

    return X_3d, explained


def main():
    parser = argparse.ArgumentParser(description="Precompute concept 3D positions via TF-IDF + PCA")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    # 1. Fetch all concepts with chapter links
    print("Fetching concepts from Neo4j...")
    rows = read_query("""
        MATCH (c:Concept)
        OPTIONAL MATCH (c)<-[:REQUIRES]-(sec:Section)<-[:CONTAINS]-(ch:Chapter)
                        <-[:CONTAINS]-(t:Textbook)<-[:CONTAINS]-(subj:Subject)
        RETURN c.id   AS id,
               c.name AS name,
               collect(DISTINCT ch.id)    AS chapter_ids,
               collect(DISTINCT subj.name)[0] AS subject
        ORDER BY c.name
    """)
    print(f"  Found {len(rows)} concepts")

    if not rows:
        print("No concepts found.")
        return

    ids = [r["id"] for r in rows]
    names = [r["name"] for r in rows]
    chapter_ids_map = {r["id"]: r["chapter_ids"] for r in rows}
    subject_map = {r["id"]: r["subject"] for r in rows}

    # 2. Build TF-IDF embeddings
    print("Building TF-IDF vectors...")
    X = build_tfidf(names)
    print(f"  Matrix shape: {X.shape} (concepts × vocabulary)")

    # 3. PCA → 3D
    print("Running PCA (3 components)...")
    X_3d, explained = pca_3d(X)
    print(f"  Explained variance: PC1={explained[0]:.3f}, PC2={explained[1]:.3f}, PC3={explained[2]:.3f}")
    print(f"  Total explained: {explained.sum():.3f}")

    # 4. Normalize onto unit sphere
    norms = np.linalg.norm(X_3d, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_sphere = X_3d / norms

    # 5. Build output
    concepts = []
    for i, concept_id in enumerate(ids):
        concepts.append({
            "id": concept_id,
            "name": names[i],
            "x": round(float(X_sphere[i, 0]), 6),
            "y": round(float(X_sphere[i, 1]), 6),
            "z": round(float(X_sphere[i, 2]), 6),
            "chapter_ids": chapter_ids_map.get(concept_id, []),
            "subject": subject_map.get(concept_id),
        })

    output_path = args.output or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "public", "concept-positions.json",
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "concepts": concepts,
            "pca_explained_variance": [round(float(v), 6) for v in explained],
            "total_concepts": len(concepts),
        }, f, indent=2)

    print(f"\nWrote {len(concepts)} concept positions to {output_path}")


if __name__ == "__main__":
    main()
