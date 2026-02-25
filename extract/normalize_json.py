"""
Normalize all chapter JSON files in the data/ directory.

This script re-normalizes concept and section prerequisite references
to ensure consistent formatting before seeding into Neo4j.

Usage:
    uv run python -m extract.normalize_json

Run this idempotently after extraction or whenever JSON files are updated.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def normalize_concept_ref(ref: str) -> str:
    """Normalize a concept reference to 'concept:snake_case' format."""
    s = ref.strip()
    if s.lower().startswith("concept:"):
        s = s[len("concept:"):]
    s = s.lower()
    s = s.replace("'", "").replace("\u2019", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return f"concept:{s}"


def normalize_section_ref(ref: str, id_prefix: str) -> str | None:
    """
    Normalize a section prerequisite reference to full format.
    Returns None if the ref is unparseable (bare text like "Unit 1").
    
    Examples:
        "1.1"                     → "ncert:physics:11:1:1.1"
        "1.10.1"                  → "ncert:physics:11:1:1.10.1"
        "SUMMARY"                 → "ncert:physics:11:1:SUMMARY"
        "ncert:physics:11:1:7:1"  → "ncert:physics:11:1:7.1"
        "ncert:physics:11:1:1.1"  → "ncert:physics:11:1:1.1" (unchanged)
        "ncert:biology:11:2"      → "ncert:biology:11:2" (cross-chapter, kept as-is)
        "ncert:chem:12:6:8:2"     → "ncert:chem:12:6:8.2" (cross-chapter, colon→dot)
        "9.2 Alkanes"             → None (unparseable bare text)
    """
    ref = ref.strip()

    # Case 1: Bare section number or SUMMARY
    if re.match(r"^[\d.]+$", ref) or ref.upper() == "SUMMARY":
        return f"{id_prefix}:{ref}"

    # Case 2: Full ncert: format (same chapter or cross-chapter)
    m = re.match(r"^(ncert:\w+:\d+:\d+)(?::(.+))?$", ref)
    if m:
        prefix = m.group(1)  # e.g. ncert:biology:11:2
        suffix = m.group(2)  # e.g. "8:2" or "1.1" or None (chapter-level ref)
        if suffix and ":" in suffix:
            suffix = suffix.replace(":", ".")
        return f"{prefix}:{suffix}" if suffix else prefix

    # Case 3: Bare text that can't be parsed (e.g. "9.2 Alkanes", "Unit 1")
    # These are LLM extraction errors — drop them
    return None


def normalize_chapter_json(json_path: str) -> dict:
    """Normalize a single chapter JSON file. Returns summary of changes."""
    with open(json_path) as f:
        data = json.load(f)

    curriculum = data["curriculum"]
    subject = data["subject"]
    grade = data["grade"]
    chapter_number = data["chapter"]["number"]
    id_prefix = f"{curriculum}:{subject}:{grade}:{chapter_number}"

    changes = {"concepts": 0, "sections": 0, "tests": 0, "deduped": 0, "dropped": 0}

    # Normalize section prerequisites
    for sec in data["chapter"]["sections"]:
        normalized_prereqs = []
        seen_refs = set()

        for prereq in sec.get("prerequisites", []):
            old_ref = prereq["ref"]

            if prereq["type"] == "concept":
                prereq["ref"] = normalize_concept_ref(prereq["ref"])
                if prereq["ref"] != old_ref:
                    changes["concepts"] += 1
            elif prereq["type"] == "section":
                new_ref = normalize_section_ref(prereq["ref"], id_prefix)
                if new_ref is None:
                    # Unparseable bare text — drop it
                    changes["dropped"] += 1
                    continue
                prereq["ref"] = new_ref
                if prereq["ref"] != old_ref:
                    changes["sections"] += 1

            # Deduplicate
            if prereq["ref"] not in seen_refs:
                seen_refs.add(prereq["ref"])
                normalized_prereqs.append(prereq)
            else:
                changes["deduped"] += 1

        sec["prerequisites"] = normalized_prereqs

    # Normalize exercise tests
    exercises = data["chapter"].get("exercises")
    if exercises:
        for item in exercises.get("items", []):
            normalized = []
            for tc in item.get("tests", []):
                # Section refs (like "ncert:physics:11:1:1.1") should NOT be
                # converted to concept format — leave them as-is.
                if tc.startswith("ncert:") or re.match(r"^concept:ncert_", tc):
                    normalized.append(tc)
                    continue
                new_tc = normalize_concept_ref(tc)
                if new_tc != tc:
                    changes["tests"] += 1
                normalized.append(new_tc)
            item["tests"] = normalized

    # Save
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return changes


def main():
    data_dir = Path("data")
    if not data_dir.exists():
        print("No data/ directory found.")
        sys.exit(1)

    json_files = sorted(data_dir.glob("ncert_*.json"))
    # Exclude progress files
    json_files = [f for f in json_files if ".progress." not in f.name]

    if not json_files:
        print("No chapter JSON files found in data/")
        sys.exit(1)

    print(f"\n🔧 Normalizing {len(json_files)} chapter JSON files...\n")

    total_changes = {"concepts": 0, "sections": 0, "tests": 0, "deduped": 0}

    for json_path in json_files:
        changes = normalize_chapter_json(str(json_path))
        total = sum(changes.values())

        if total > 0:
            print(f"  ✏️  {json_path.name}: {changes}")
        else:
            print(f"  ✅ {json_path.name}: already normalized")

        for k in total_changes:
            total_changes[k] += changes[k]

    print(f"\n📊 Total changes: {total_changes}")
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
