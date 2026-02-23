"""
One-time script to remove unit preface sections from biology JSON files.
These sections contain unit introductions and scientist biographies that
were incorrectly extracted from PDF pages preceding the actual chapter.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Map of file -> number of leading preface sections to remove
FIXES = {
    "ncert_biology_11_ch1.json": 2,   # "Diversity in the Living World" + "Ernst Mayr"
    "ncert_biology_11_ch5.json": 1,   # "Structural Organisation in Plants and Animals"
    "ncert_biology_11_ch8.json": 1,   # "Cell: Structure and Functions"
    "ncert_biology_11_ch11.json": 1,  # "Plant Physiology"
    "ncert_biology_11_ch14.json": 2,  # "Human Physiology" + "Alfonso Corti"
    "ncert_biology_12_ch1.json": 2,   # "Reproduction" + "Panchanan Maheshwari"
    "ncert_biology_12_ch4.json": 1,   # "Genetics and Evolution"
    "ncert_biology_12_ch7.json": 1,   # "Biology in Human Welfare"
    "ncert_biology_12_ch11.json": 2,  # "Ecology" + "Ramdeo Misra"
}


def main():
    for filename, drop_count in FIXES.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"  SKIP (not found): {filename}")
            continue

        with open(filepath) as f:
            data = json.load(f)

        sections = data["chapter"]["sections"]
        original_count = len(sections)

        # Print what we're removing
        removed = sections[:drop_count]
        for s in removed:
            print(f"  Removing sec number={s.get('number')}, title=\"{s['title']}\"")

        # Remove preface sections (keep section numbers as-is)
        data["chapter"]["sections"] = sections[drop_count:]
        new_count = len(data["chapter"]["sections"])

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        new_first = data["chapter"]["sections"][0]
        print(
            f"  ✓ {filename}: {original_count} → {new_count} sections. "
            f"New first: [{new_first.get('number')}] \"{new_first['title']}\""
        )
        print()


if __name__ == "__main__":
    main()
