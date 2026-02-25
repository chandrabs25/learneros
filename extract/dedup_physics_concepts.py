"""
Deduplicate and normalize physics concept names.

Usage:
    python extract/dedup_physics_concepts.py
    python extract/dedup_physics_concepts.py --dry-run
"""
import json
import glob
import sys

MERGE_MAP = {
    # Same concept, different names
    "concept:amperes_circuital_law": "concept:amperes_law",
    "concept:work_and_energy": "concept:work",
    "concept:linear_momentum": "concept:momentum",
    "concept:charge_conservation_in_circuits": "concept:conservation_of_charge",

    # Subset → parent
    "concept:p_n_junction_v_i_characteristics": "concept:p_n_junction",
    "concept:elasticity_modulus": "concept:elasticity",
    "concept:shear_stress_and_strain": "concept:stress_and_strain",
    "concept:uniform_circular_motion": "concept:circular_motion",
}


def process_file(filepath: str, dry_run: bool = False) -> dict:
    with open(filepath) as f:
        data = json.load(f)

    bn = filepath.split("/")[-1]
    ch = data["chapter"]
    changes = {"merged": 0}

    # Section prerequisites
    for sec in ch.get("sections", []):
        seen = set()
        new_prereqs = []
        for prereq in sec.get("prerequisites", []):
            if prereq.get("type") == "concept" and prereq["ref"] in MERGE_MAP:
                prereq["ref"] = MERGE_MAP[prereq["ref"]]
                changes["merged"] += 1
            key = (prereq.get("type"), prereq.get("ref"))
            if key not in seen:
                seen.add(key)
                new_prereqs.append(prereq)
        sec["prerequisites"] = new_prereqs

    # Exercise tests
    exercises = ch.get("exercises")
    if exercises and isinstance(exercises, dict):
        for item in exercises.get("items", []):
            seen = set()
            new_tc = []
            for tc in item.get("tests", []):
                if tc in MERGE_MAP:
                    tc = MERGE_MAP[tc]
                    changes["merged"] += 1
                if tc not in seen:
                    seen.add(tc)
                    new_tc.append(tc)
            item["tests"] = new_tc

    if not dry_run and changes["merged"]:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    files = sorted(f for f in glob.glob("data/ncert_physics_*.json")
                   if ".raw." not in f and ".progress." not in f)

    print(f"\n🔧 Deduplicating concepts in {len(files)} physics files {'(DRY RUN)' if dry_run else ''}...\n")
    total = 0
    for fp in files:
        changes = process_file(fp, dry_run)
        if changes["merged"]:
            print(f"  ✏️  {fp.split('/')[-1]}: {changes['merged']} merged")
            total += changes["merged"]
        else:
            print(f"  ✅ {fp.split('/')[-1]}: clean")

    print(f"\n📊 Total merged: {total}\n✅ Done!\n")


if __name__ == "__main__":
    main()
