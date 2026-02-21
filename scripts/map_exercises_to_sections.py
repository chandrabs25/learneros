"""
Map exercises to their most relevant section using Fireworks-hosted Kimi 2.5.

For each chapter:
  1. Fetch all sections (id + title + summary/content)
  2. Fetch all exercises (id + problem text)
  3. For each exercise, call Kimi to determine the best matching section
  4. Update the TESTS relationship in Neo4j (delete old, create new)

Usage:
  cd backend && uv run python3 ../scripts/map_exercises_to_sections.py

Environment variables (reads from backend/.env):
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
  FIREWORKS_API_KEY, FIREWORKS_BASE_URL, FIREWORKS_MODEL
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from dotenv import load_dotenv

# Load env from backend/.env
backend_dir = Path(__file__).resolve().parent.parent / "backend"
load_dotenv(backend_dir / ".env")

from neo4j import GraphDatabase
from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────────
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
FIREWORKS_API_KEY = os.environ["FIREWORKS_API_KEY"]
FIREWORKS_BASE_URL = os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
FIREWORKS_MODEL = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/kimi-k2p5")

MODEL = FIREWORKS_MODEL
RATE_LIMIT_DELAY = 0.3  # seconds between API calls to avoid quota issues

# ── Neo4j helpers ───────────────────────────────────────────────────
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def fetch_all_chapters():
    """Return all chapter IDs."""
    with driver.session() as session:
        result = session.run(
            "MATCH (ch:Chapter) RETURN ch.id AS id, ch.title AS title ORDER BY ch.id"
        )
        return [dict(r) for r in result]


def fetch_sections_for_chapter(chapter_id: str):
    """Return sections with their titles for a given chapter."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (ch:Chapter {id: $chapter_id})-[:CONTAINS]->(sec:Section)
            WHERE NOT sec.title STARTS WITH 'Summary'
              AND NOT sec.title STARTS WITH 'Points to Ponder'
              AND NOT sec.title STARTS WITH 'Exercises'
            OPTIONAL MATCH (sec)-[:CONTAINS]->(ss:Subsection)
            WITH sec, collect(ss.title) AS subsection_titles
            RETURN sec.id AS id,
                   sec.number AS number,
                   sec.title AS title,
                   subsection_titles
            ORDER BY sec.order
            """,
            chapter_id=chapter_id,
        )
        return [dict(r) for r in result]


def fetch_exercises_for_chapter(chapter_id: str):
    """Return exercises for a given chapter."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (ch:Chapter {id: $chapter_id})-[:HAS_EXERCISE_SET]->(es:ExerciseSet)-[:CONTAINS]->(ex:Exercise)
            RETURN ex.id AS id,
                   ex.number AS number,
                   ex.problem AS problem,
                   ex.difficulty AS difficulty,
                   ex.exercise_type AS exercise_type
            ORDER BY ex.number
            """,
            chapter_id=chapter_id,
        )
        return [dict(r) for r in result]


def update_tests_relationship(exercise_id: str, section_id: str):
    """Delete old TESTS relationships and create a new one."""
    with driver.session() as session:
        session.run(
            """
            MATCH (e:Exercise {id: $exercise_id})-[r:TESTS]->()
            DELETE r
            """,
            exercise_id=exercise_id,
        )
        session.run(
            """
            MATCH (e:Exercise {id: $exercise_id})
            MATCH (s:Section {id: $section_id})
            MERGE (e)-[r:TESTS]->(s)
            SET r.source = $model, r.mapped_at = datetime()
            """,
            exercise_id=exercise_id,
            section_id=section_id,
            model=MODEL,
        )


# ── Fireworks Kimi helper ───────────────────────────────────────────
client = OpenAI(api_key=FIREWORKS_API_KEY, base_url=FIREWORKS_BASE_URL)


def ask_kimi_for_section(exercise_problem: str, sections: list[dict]) -> str | None:
    """
    Ask Kimi which section best matches an exercise question.
    Returns the section ID or None if it can't determine.
    """
    # Build section list for the prompt
    section_list = "\n".join(
        f"  - ID: {s['id']} | Title: {s['title']}"
        + (f" | Subtopics: {', '.join(s['subsection_titles'][:5])}" if s.get("subsection_titles") else "")
        for s in sections
    )

    prompt = f"""You are a physics/chemistry/biology subject expert. Given an exercise question from an NCERT textbook and a list of sections from the same chapter, determine which ONE section is the best match for this exercise — i.e., which section's concepts are being tested by this question.

## Available Sections:
{section_list}

## Exercise Question:
{exercise_problem}

## Instructions:
- Respond with ONLY the section ID (e.g., "ncert:physics:12:1:1.5") — nothing else.
- Pick the MOST SPECIFIC section that directly covers the concepts tested.
- If the question tests multiple concepts, pick the PRIMARY one.
- Do NOT include any explanation, just the section ID."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Return only the section ID and nothing else."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=60,
        )
        answer = (response.choices[0].message.content or "").strip().strip('"').strip("'").strip("`")
        # Basic validation: the answer should look like a section ID
        if answer.startswith("ncert:"):
            return answer
        # Try to extract section ID from the response
        match = re.search(r"(ncert:\S+)", answer)
        if match:
            return match.group(1)
        print(f"    ⚠ Unexpected response: {answer[:100]}")
        return None
    except Exception as e:
        print(f"    ❌ Kimi error: {e}")
        return None


# ── Main ────────────────────────────────────────────────────────────
def process_chapter(chapter_id: str, chapter_title: str):
    """Process all exercises in a chapter."""
    sections = fetch_sections_for_chapter(chapter_id)
    exercises = fetch_exercises_for_chapter(chapter_id)

    if not sections or not exercises:
        print(f"  ⏭ Skipping (sections: {len(sections)}, exercises: {len(exercises)})")
        return 0, 0

    section_ids = {s["id"] for s in sections}
    updated = 0
    failed = 0

    for ex in exercises:
        print(f"  Q{ex['number']}: {ex['problem'][:70]}...")

        best_section_id = ask_kimi_for_section(ex["problem"], sections)

        if best_section_id and best_section_id in section_ids:
            update_tests_relationship(ex["id"], best_section_id)
            # Find the section title for display
            sec_title = next((s["title"] for s in sections if s["id"] == best_section_id), "?")
            print(f"    ✅ → {best_section_id} ({sec_title})")
            updated += 1
        elif best_section_id:
            print(f"    ⚠ Section ID not found in chapter: {best_section_id}")
            failed += 1
        else:
            print(f"    ❌ Could not determine section")
            failed += 1

        time.sleep(RATE_LIMIT_DELAY)

    return updated, failed


def main():
    chapters = fetch_all_chapters()
    print(f"Found {len(chapters)} chapters\n")

    total_updated = 0
    total_failed = 0

    for ch in chapters:
        print(f"\n{'='*60}")
        print(f"📖 {ch['id']} — {ch['title']}")
        print(f"{'='*60}")

        updated, failed = process_chapter(ch["id"], ch["title"])
        total_updated += updated
        total_failed += failed

        print(f"  📊 Updated: {updated}, Failed: {failed}")

    print(f"\n{'='*60}")
    print(f"🏁 DONE — Total Updated: {total_updated}, Total Failed: {total_failed}")
    print(f"{'='*60}")

    driver.close()


if __name__ == "__main__":
    main()
