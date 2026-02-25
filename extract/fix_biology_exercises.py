"""
One-time script to standardize biology exercise formats and strip solutions.

- Converts plain list exercises → dict format with {title, items}
- Strips 'solution' keys from exercise items
- Ensures consistent item structure: {number, problem, tests}

Usage:
    python extract/fix_biology_exercises.py
"""
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def parse_number_from_text(text: str) -> int | None:
    """Extract leading question number from exercise text like '1.  What is...'"""
    m = re.match(r"^\**(\d+)[\.\)\*]", text.strip())
    return int(m.group(1)) if m else None


def normalize_exercises(filepath: Path) -> dict:
    """Normalize exercises for a single file. Returns summary of changes."""
    with open(filepath) as f:
        data = json.load(f)

    ch = data["chapter"]
    exercises = ch.get("exercises")
    changes = {"converted": False, "solutions_stripped": 0, "items_fixed": 0}

    if exercises is None:
        return changes

    # --- Convert list format → dict format ---
    if isinstance(exercises, list):
        items = []
        for i, ex in enumerate(exercises):
            if isinstance(ex, str):
                num = parse_number_from_text(ex)
                # Strip leading number prefix from problem text
                problem = re.sub(r"^\**\d+[\.\)\*]+\s*", "", ex).strip()
                items.append({
                    "number": num or (i + 1),
                    "problem": problem,
                    "tests": [],
                })
            elif isinstance(ex, dict):
                items.append(ex)
        ch["exercises"] = {"title": "Exercises", "items": items}
        changes["converted"] = True
        exercises = ch["exercises"]

    # --- Ensure it's a dict with items ---
    if not isinstance(exercises, dict):
        return changes

    items = exercises.get("items", [])

    for item in items:
        # Strip solutions
        if "solution" in item and item["solution"] is not None:
            del item["solution"]
            changes["solutions_stripped"] += 1

        # Strip other generated fields we don't want
        for key in ["difficulty", "exercise_type"]:
            if key in item:
                del item[key]
                changes["items_fixed"] += 1

        # Ensure tests exists
        if "tests" not in item:
            item["tests"] = []
            changes["items_fixed"] += 1

        # Ensure number and problem exist
        if "number" not in item:
            changes["items_fixed"] += 1
        if "problem" not in item:
            changes["items_fixed"] += 1

    # Save
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return changes


def main():
    files = sorted(DATA_DIR.glob("ncert_biology_*.json"))
    print(f"\n🔧 Normalizing exercises in {len(files)} biology files...\n")

    total = {"converted": 0, "solutions_stripped": 0, "items_fixed": 0}

    for fp in files:
        changes = normalize_exercises(fp)
        any_change = changes["converted"] or changes["solutions_stripped"] or changes["items_fixed"]

        if any_change:
            parts = []
            if changes["converted"]:
                parts.append("list→dict")
                total["converted"] += 1
            if changes["solutions_stripped"]:
                parts.append(f"{changes['solutions_stripped']} solutions stripped")
                total["solutions_stripped"] += changes["solutions_stripped"]
            if changes["items_fixed"]:
                parts.append(f"{changes['items_fixed']} items fixed")
                total["items_fixed"] += changes["items_fixed"]
            print(f"  ✏️  {fp.name}: {', '.join(parts)}")
        else:
            print(f"  ✅ {fp.name}: OK")

    print(f"\n📊 Total: {total}")
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
