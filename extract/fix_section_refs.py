"""
Fix section references incorrectly stored as concept:ncert_* in tests.

Converts entries like:
  "concept:ncert_physics_11_1_1_1"  → "ncert:physics:11:1:1.1"
  "concept:ncert_chemistry_12_3_3_2" → "ncert:chemistry:12:3:3.2"

Usage:
    python extract/fix_section_refs.py              # fix all
    python extract/fix_section_refs.py --dry-run     # preview only
"""
import json
import glob
import re
import sys


def convert_ref(ref: str) -> str | None:
    """Convert concept:ncert_subject_grade_chapter_section... to proper section ID."""
    # Match: concept:ncert_{subject}_{grade}_{chapter}_{section parts}
    m = re.match(r'^concept:ncert_(\w+?)_(\d+)_(\d+)_(.+)$', ref)
    if not m:
        return None

    subject = m.group(1)
    grade = m.group(2)
    chapter = m.group(3)
    rest = m.group(4)

    # Convert underscore-separated section parts to dot notation
    # e.g., "1_1" → "1.1", "1_3_1" → "1.3.1", "summary" → "Summary"
    parts = rest.split("_")

    # Check if all parts are numeric → section number like 1.1 or 1.3.1
    if all(p.isdigit() for p in parts):
        section_num = ".".join(parts)
    else:
        # Non-numeric like "summary" → capitalize
        section_num = "_".join(parts).title()

    return f"ncert:{subject}:{grade}:{chapter}:{section_num}"


def process_file(filepath: str, dry_run: bool = False) -> dict:
    with open(filepath) as f:
        data = json.load(f)

    bn = filepath.split("/")[-1]
    ch = data["chapter"]
    fixed = 0
    dropped = 0

    exercises = ch.get("exercises")
    if not exercises or not isinstance(exercises, dict):
        return {"file": bn, "fixed": 0, "dropped": 0}

    for item in exercises.get("items", []):
        new_tc = []
        seen = set()
        for tc in item.get("tests", []):
            if tc.startswith("concept:ncert_"):
                converted = convert_ref(tc)
                if converted and converted not in seen:
                    new_tc.append(converted)
                    seen.add(converted)
                    fixed += 1
                else:
                    dropped += 1
            else:
                if tc not in seen:
                    new_tc.append(tc)
                    seen.add(tc)
        item["tests"] = new_tc

    if not dry_run and (fixed or dropped):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return {"file": bn, "fixed": fixed, "dropped": dropped}


def main():
    dry_run = "--dry-run" in sys.argv

    files = sorted(
        f for f in glob.glob("data/ncert_*.json")
        if ".raw." not in f and ".progress." not in f
    )

    print(f"\n🔧 Fixing section refs in tests {'(DRY RUN)' if dry_run else ''}\n")

    total_fixed = 0
    total_dropped = 0
    for fp in files:
        r = process_file(fp, dry_run)
        if r["fixed"] or r["dropped"]:
            print(f"  ✏️  {r['file']}: {r['fixed']} fixed, {r['dropped']} dropped")
            total_fixed += r["fixed"]
            total_dropped += r["dropped"]

    print(f"\n{'='*50}")
    print(f"✅ Fixed: {total_fixed}, Dropped: {total_dropped}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
