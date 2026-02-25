"""
Seed Script — Ingest a textbook chapter JSON into Neo4j.

Usage:
    python -m db.seed data/sample_chapter.json

This script:
1. Validates the JSON against the Pydantic models
2. Ensures Curriculum, Subject, and Textbook nodes exist (MERGE)
3. Creates Chapter, Section, Subsection, WorkedExample, Diagram nodes
4. Creates ExerciseSet and Exercise nodes
5. Builds CONTAINS, NEXT, HAS_EXERCISE_SET, HAS_WORKED_EXAMPLE, HAS_DIAGRAM relationships
6. Links prerequisites via REQUIRES relationships
7. Links concept references via TEACHES_CONCEPT relationships
"""

from __future__ import annotations

import json
import os
import sys
import uuid

from dotenv import load_dotenv
from neo4j import GraphDatabase

from db.models import TextbookChapter

load_dotenv()

# =============================================================================
# Neo4j Connection
# =============================================================================


def get_driver():
    """Create a Neo4j driver from environment variables."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


# =============================================================================
# Schema Setup
# =============================================================================


def run_schema(session):
    """Run the schema.cypher file to create constraints and indexes."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.cypher")
    with open(schema_path) as f:
        content = f.read()

    # Split on semicolons, skip comments and empty lines
    statements = []
    for stmt in content.split(";"):
        stmt = stmt.strip()
        # Remove comment-only lines
        lines = [line for line in stmt.split("\n") if not line.strip().startswith("//")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)

    for stmt in statements:
        try:
            session.run(stmt)
        except Exception as e:
            # Constraints/indexes may already exist
            print(f"  ⚠ Schema statement skipped (may already exist): {e}")


# =============================================================================
# Seeding Functions
# =============================================================================


def seed_curriculum_hierarchy(tx, data: TextbookChapter):
    """Create or merge Curriculum → Subject → Textbook hierarchy."""

    # Curriculum
    tx.run(
        """
        MERGE (c:Curriculum {id: $id})
        SET c.name = $name, c.country = $country
        """,
        id=data.curriculum,
        name=data.curriculum.upper(),
        country="India",  # Default for NCERT
    )

    # Subject
    subject_id = f"{data.curriculum}:{data.subject}"
    tx.run(
        """
        MERGE (s:Subject {id: $id})
        SET s.name = $name
        WITH s
        MATCH (c:Curriculum {id: $curriculum_id})
        MERGE (c)-[:CONTAINS]->(s)
        """,
        id=subject_id,
        name=data.subject.title(),
        curriculum_id=data.curriculum,
    )

    # Textbook
    textbook_id = data.build_id_prefix()
    tx.run(
        """
        MERGE (t:Textbook {id: $id})
        SET t.name = $name, t.grade = $grade, t.volume = $volume
        WITH t
        MATCH (s:Subject {id: $subject_id})
        MERGE (s)-[:CONTAINS]->(t)
        """,
        id=textbook_id,
        name=data.textbook_name,
        grade=data.grade,
        volume=data.volume,
        subject_id=subject_id,
    )

    return textbook_id


def seed_chapter(tx, data: TextbookChapter, textbook_id: str):
    """Create Chapter node and link to Textbook."""

    chapter_id = data.build_chapter_id()
    tx.run(
        """
        MERGE (ch:Chapter {id: $id})
        SET ch.number = $number, ch.title = $title, ch.summary = $summary
        WITH ch
        MATCH (t:Textbook {id: $textbook_id})
        MERGE (t)-[:CONTAINS]->(ch)
        """,
        id=chapter_id,
        number=data.chapter.number,
        title=data.chapter.title,
        summary=data.chapter.summary or "",
        textbook_id=textbook_id,
    )

    return chapter_id


def seed_sections(tx, data: TextbookChapter, chapter_id: str):
    """Create Section, Subsection, WorkedExample, and Diagram nodes."""

    prefix = data.build_id_prefix()
    ch_num = data.chapter.number
    prev_section_id = None

    for section in data.chapter.sections:
        # Use full section number as ID suffix (e.g., "1.7.1" → "ncert:physics:11:1:1.7.1")
        section_id = f"{prefix}:{ch_num}:{section.number}"

        # Create Section
        tx.run(
            """
            MERGE (sec:Section {id: $id})
            SET sec.number = $number, sec.title = $title, 
                sec.content_text = $content_text
            WITH sec
            MATCH (ch:Chapter {id: $chapter_id})
            MERGE (ch)-[:CONTAINS]->(sec)
            """,
            id=section_id,
            number=section.number,
            title=section.title,
            content_text=section.content_text or "",
            chapter_id=chapter_id,
        )

        # NEXT relationship between sections
        if prev_section_id:
            tx.run(
                """
                MATCH (prev:Section {id: $prev_id})
                MATCH (curr:Section {id: $curr_id})
                MERGE (prev)-[:NEXT]->(curr)
                """,
                prev_id=prev_section_id,
                curr_id=section_id,
            )
        prev_section_id = section_id

        # Subsections
        prev_subsection_id = None
        for subsection in section.subsections:
            subsection_id = f"{section_id}:{subsection.order}"

            tx.run(
                """
                MERGE (ss:Subsection {id: $id})
                SET ss.order = $order, ss.title = $title,
                    ss.content_text = $content_text,
                    ss.content_type = $content_type
                WITH ss
                MATCH (sec:Section {id: $section_id})
                MERGE (sec)-[:CONTAINS]->(ss)
                """,
                id=subsection_id,
                order=subsection.order,
                title=subsection.title,
                content_text=subsection.content_text,
                content_type=subsection.content_type.value,
                section_id=section_id,
            )

            # NEXT between subsections
            if prev_subsection_id:
                tx.run(
                    """
                    MATCH (prev:Subsection {id: $prev_id})
                    MATCH (curr:Subsection {id: $curr_id})
                    MERGE (prev)-[:NEXT]->(curr)
                    """,
                    prev_id=prev_subsection_id,
                    curr_id=subsection_id,
                )
            prev_subsection_id = subsection_id

            # Worked Examples
            for idx, we in enumerate(subsection.worked_examples, 1):
                we_id = f"{subsection_id}:we{idx}"
                tx.run(
                    """
                    MERGE (we:WorkedExample {id: $id})
                    SET we.label = $label, we.problem = $problem,
                        we.solution = $solution, we.order = $order
                    WITH we
                    MATCH (ss:Subsection {id: $subsection_id})
                    MERGE (ss)-[:HAS_WORKED_EXAMPLE]->(we)
                    """,
                    id=we_id,
                    label=we.label,
                    problem=we.problem,
                    solution=we.solution,
                    order=idx,
                    subsection_id=subsection_id,
                )

            # Diagrams
            for idx, diag in enumerate(subsection.diagrams, 1):
                diag_id = f"{subsection_id}:d{idx}"
                tx.run(
                    """
                    MERGE (d:Diagram {id: $id})
                    SET d.label = $label, d.description = $description,
                        d.image_url = $image_url
                    WITH d
                    MATCH (ss:Subsection {id: $subsection_id})
                    MERGE (ss)-[:HAS_DIAGRAM]->(d)
                    """,
                    id=diag_id,
                    label=diag.label,
                    description=diag.description,
                    image_url=diag.image_url or "",
                    subsection_id=subsection_id,
                )

            # Tables
            for idx, table in enumerate(subsection.tables, 1):
                table_id = f"{subsection_id}:t{idx}"
                tx.run(
                    """
                    MERGE (t:Table {id: $id})
                    SET t.label = $label, t.caption = $caption,
                        t.headers = $headers, t.rows_json = $rows_json
                    WITH t
                    MATCH (ss:Subsection {id: $subsection_id})
                    MERGE (ss)-[:HAS_TABLE]->(t)
                    """,
                    id=table_id,
                    label=table.label or "",
                    caption=table.caption or "",
                    headers=table.headers,
                    rows_json=json.dumps(table.rows, ensure_ascii=False),
                    subsection_id=subsection_id,
                )

        # Prerequisites
        for prereq in section.prerequisites:
            if prereq.type.value == "concept":
                # Ensure the Concept node exists, then link REQUIRES
                tx.run(
                    """
                    MERGE (c:Concept {id: $concept_id})
                    ON CREATE SET c.name = $concept_name
                    WITH c
                    MATCH (sec:Section {id: $section_id})
                    MERGE (sec)-[:REQUIRES]->(c)
                    """,
                    concept_id=prereq.ref,
                    concept_name=prereq.ref.replace("concept:", "").replace("-", " ").title(),
                    section_id=section_id,
                )
            else:
                # Section prerequisite — link REQUIRES only if target exists.
                # Use MATCH (not MERGE) to avoid creating phantom Section nodes
                # for cross-chapter refs that don't match real section IDs.
                result = tx.run(
                    """
                    MATCH (sec:Section {id: $section_id})
                    MATCH (prereq:Section {id: $prereq_id})
                    MERGE (sec)-[:REQUIRES]->(prereq)
                    RETURN prereq.id AS matched
                    """,
                    section_id=section_id,
                    prereq_id=prereq.ref,
                )
                if not result.single():
                    print(f"  ⚠️  Skipping prerequisite: section '{prereq.ref}' not found in DB")


def seed_exercises(tx, data: TextbookChapter, chapter_id: str):
    """Create ExerciseSet and Exercise nodes."""

    if not data.chapter.exercises:
        return

    exercises = data.chapter.exercises
    exercise_set_id = f"{data.build_chapter_id()}:ex"

    # ExerciseSet
    tx.run(
        """
        MERGE (es:ExerciseSet {id: $id})
        SET es.title = $title
        WITH es
        MATCH (ch:Chapter {id: $chapter_id})
        MERGE (ch)-[:HAS_EXERCISE_SET]->(es)
        """,
        id=exercise_set_id,
        title=exercises.title,
        chapter_id=chapter_id,
    )

    # Exercises
    for item in exercises.items:
        exercise_id = f"{exercise_set_id}:{item.number}"

        tx.run(
            """
            MERGE (e:Exercise {id: $id})
            SET e.number = $number, e.problem = $problem,
                e.solution = $solution, e.difficulty = $difficulty,
                e.exercise_type = $exercise_type
            WITH e
            MATCH (es:ExerciseSet {id: $exercise_set_id})
            MERGE (es)-[:CONTAINS]->(e)
            """,
            id=exercise_id,
            number=item.number,
            problem=item.problem,
            solution=item.solution or "",
            difficulty=item.difficulty.value if item.difficulty else "",
            exercise_type=item.exercise_type.value if item.exercise_type else "",
            exercise_set_id=exercise_set_id,
        )

        # Link exercise to concepts/sections it tests
        for concept_ref in item.tests:
            if concept_ref.startswith("concept:") and not concept_ref.startswith("concept:ncert_"):
                tx.run(
                    """
                    MERGE (c:Concept {id: $concept_id})
                    ON CREATE SET c.name = $concept_name
                    WITH c
                    MATCH (e:Exercise {id: $exercise_id})
                    MERGE (e)-[:TESTS]->(c)
                    """,
                    concept_id=concept_ref,
                    concept_name=concept_ref.replace("concept:", "").replace("-", " ").title(),
                    exercise_id=exercise_id,
                )
            else:
                # References a section
                tx.run(
                    """
                    MATCH (e:Exercise {id: $exercise_id})
                    MERGE (target:Section {id: $target_id})
                    MERGE (e)-[:TESTS]->(target)
                    """,
                    exercise_id=exercise_id,
                    target_id=concept_ref,
                )


# =============================================================================
# Main
# =============================================================================


def seed_chapter_from_json(json_path: str):
    """Main entry point: validate JSON and seed into Neo4j."""

    print(f"\n📖 Loading chapter from: {json_path}")

    with open(json_path) as f:
        raw = json.load(f)

    # Validate with Pydantic
    data = TextbookChapter(**raw)
    print(f"✅ Validated: {data.curriculum}:{data.subject} Grade {data.grade} — "
          f"Chapter {data.chapter.number}: {data.chapter.title}")
    print(f"   Sections: {len(data.chapter.sections)}")
    total_subsections = sum(len(s.subsections) for s in data.chapter.sections)
    print(f"   Subsections: {total_subsections}")
    if data.chapter.exercises:
        print(f"   Exercises: {len(data.chapter.exercises.items)}")

    driver = get_driver()

    with driver.session() as session:
        # Run schema setup
        print("\n🔧 Setting up schema constraints & indexes...")
        run_schema(session)

        # Seed data
        print("📝 Seeding curriculum hierarchy...")
        textbook_id = session.execute_write(seed_curriculum_hierarchy, data)

        print("📝 Seeding chapter...")
        chapter_id = session.execute_write(seed_chapter, data, textbook_id)

        print("📝 Seeding sections, subsections, examples, diagrams...")
        session.execute_write(seed_sections, data, chapter_id)

        print("📝 Seeding exercises...")
        session.execute_write(seed_exercises, data, chapter_id)

    driver.close()
    print(f"\n🎉 Done! Chapter '{data.chapter.title}' seeded successfully.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m db.seed <path_to_chapter.json>")
        sys.exit(1)

    seed_chapter_from_json(sys.argv[1])
