"""
Extract end-of-chapter exercise problems and solutions from all
NCERT Physics chapter JSON files and consolidate into a single JSON.

Usage:
    python scripts/extract_physics_exercises.py

Output:
    data/physics_exercises.json
"""

import json
import glob
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "physics_exercises.json")
FILE_PREFIX = "ncert_physics_"


def extract_chapter_info(filepath: str) -> dict | None:
    """Extract chapter metadata and exercises from a single chapter JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    chapter = data.get("chapter", {})
    exercises_section = chapter.get("exercises", {})
    items = exercises_section.get("items", [])

    if not items:
        return None

    # Extract grade from the filename  (e.g. ncert_physics_11_ch1.json → 11)
    basename = os.path.basename(filepath)
    grade_match = re.search(r"ncert_physics_(\d+)_ch(\d+)", basename)
    grade = int(grade_match.group(1)) if grade_match else data.get("grade")
    file_chapter_num = int(grade_match.group(2)) if grade_match else None

    chapter_number = chapter.get("number", file_chapter_num)
    chapter_title = chapter.get("title", "Unknown")

    problems = []
    for item in items:
        problems.append({
            "exercise_number": item.get("number"),
            "problem": item.get("problem"),
            "solution": item.get("solution"),
            "difficulty": item.get("difficulty"),
            "exercise_type": item.get("exercise_type"),
            "tests_concepts": item.get("tests_concepts", []),
        })

    return {
        "id": f"ncert:physics:{grade}:{chapter_number}",
        "grade": grade,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "total_exercises": len(problems),
        "exercises": problems,
    }


def main():
    pattern = os.path.join(DATA_DIR, f"{FILE_PREFIX}*.json")
    files = sorted(glob.glob(pattern))

    # Exclude any .raw.json files
    files = [f for f in files if not f.endswith(".raw.json")]

    print(f"Found {len(files)} physics chapter files in {DATA_DIR}")

    all_chapters = []
    total_exercises = 0

    for filepath in files:
        result = extract_chapter_info(filepath)
        if result:
            all_chapters.append(result)
            total_exercises += result["total_exercises"]
            print(
                f"  ✓ {os.path.basename(filepath):40s} → "
                f"Ch {result['chapter_number']:>2}: {result['chapter_title'][:40]:40s} "
                f"({result['total_exercises']} exercises)"
            )
        else:
            print(f"  ✗ {os.path.basename(filepath):40s} → No exercises found")

    # Sort by grade then chapter number
    all_chapters.sort(key=lambda c: (c["grade"], c["chapter_number"]))

    output = {
        "description": "NCERT Physics end-of-chapter exercises (problems & solutions)",
        "total_chapters": len(all_chapters),
        "total_exercises": total_exercises,
        "chapters": all_chapters,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Wrote {total_exercises} exercises from {len(all_chapters)} chapters → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
