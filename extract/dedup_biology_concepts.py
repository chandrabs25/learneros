"""
Deduplicate and normalize biology concept names.

Merges near-duplicate concepts into canonical names, ensuring consistency
with chemistry/physics concepts where they overlap.

Usage:
    python extract/dedup_biology_concepts.py
    python extract/dedup_biology_concepts.py --dry-run
"""
import json
import glob
import sys
from collections import defaultdict

# -----------------------------------------------------------------------
# Concept merge mapping: old_name → canonical_name
# -----------------------------------------------------------------------
MERGE_MAP = {
    # ---------- Duplicates: merge specific into general ----------
    # Respiration
    "concept:aerobic_and_anaerobic_respiration": "concept:aerobic_respiration",

    # Classification
    "concept:whittakers_five_kingdom_classification": "concept:five_kingdom_classification",
    "concept:animal_kingdom_classification": "concept:animal_classification",

    # Cell biology
    "concept:cell_division_organelles": "concept:cell_organelles",
    "concept:cell_organelles_chloroplasts_and_mitochondria": "concept:cell_organelles",
    "concept:eukaryotic_cell_structure": "concept:cell_structure",
    "concept:plant_cell_structure": "concept:cell_structure",
    "concept:eukaryotic_cell": "concept:cell_structure",

    # DNA
    "concept:dna_and_rna_structure": "concept:dna_structure",
    "concept:dna_structure_and_replication": "concept:dna_replication",

    # Embryo
    "concept:embryo_development": "concept:embryonic_development",
    "concept:pregnancy_and_embryonic_development": "concept:embryonic_development",

    # Genetics
    "concept:genetics_and_inheritance": "concept:genetics",
    "concept:principles_of_inheritance_and_variation": "concept:inheritance",

    # Reproductive system
    "concept:human_reproductive_system": "concept:reproductive_system",

    # Nervous system
    "concept:autonomic_nervous_system": "concept:human_nervous_system",

    # Excretory system
    "concept:human_excretory_system": "concept:excretory_system",

    # Organisms
    "concept:unicellular_vs_multicellular": "concept:unicellular_and_multicellular_organisms",

    # Connective tissue
    "concept:specialized_connective_tissues_bone_and_cartilage": "concept:connective_tissue",

    # Plant anatomy — too verbose
    "concept:plant_anatomy_parenchyma_stomata_and_lenticels": "concept:plant_anatomy",

    # Circulatory system
    "concept:open_circulatory_system": "concept:circulatory_system",

    # Evolution
    "concept:evolutionary_history": "concept:evolution",

    # Hormones
    "concept:plant_hormones": "concept:plant_growth_regulators",

    # Pollen/embryo sac verbose names
    "concept:structure_of_pollen_grain_and_embryo_sac": "concept:embryo_sac_structure",

    # Vertebrate 
    "concept:vertebrate_classification": "concept:vertebrata",
}

# -----------------------------------------------------------------------
# Concepts to REMOVE entirely (too generic, not useful as prereqs)
# -----------------------------------------------------------------------
REMOVE_SET = {
    "concept:protoplasm",
    "concept:plumule",
    "concept:radula",
    "concept:stomochord",
    "concept:zygote",  # Too basic/generic
    "concept:visible_spectrum_vibgyor",  # Physics concept, not relevant for bio prereqs
    "concept:redox_potential_scale",  # Chemistry concept, not meaningful bio prereq
    "concept:pressure_gradients",  # Too generic
    "concept:states_of_matter",  # Too basic for bio prereqs
    "concept:potential_energy",  # Too basic for bio prereqs
}


def process_file(filepath: str, dry_run: bool = False) -> dict:
    """Deduplicate concepts in a single file."""
    with open(filepath) as f:
        data = json.load(f)

    bn = filepath.split("/")[-1]
    ch = data["chapter"]
    changes = {"merged": 0, "removed": 0}

    # 1. Process section prerequisites
    for sec in ch.get("sections", []):
        new_prereqs = []
        seen_refs = set()
        for prereq in sec.get("prerequisites", []):
            if prereq.get("type") != "concept":
                new_prereqs.append(prereq)
                continue

            ref = prereq["ref"]

            # Remove?
            if ref in REMOVE_SET:
                changes["removed"] += 1
                continue

            # Merge?
            if ref in MERGE_MAP:
                old = ref
                ref = MERGE_MAP[ref]
                prereq["ref"] = ref
                changes["merged"] += 1

            # Deduplicate
            if ref not in seen_refs:
                seen_refs.add(ref)
                new_prereqs.append(prereq)

        sec["prerequisites"] = new_prereqs

    # 2. Process exercise tests_concepts
    exercises = ch.get("exercises")
    if exercises and isinstance(exercises, dict):
        for item in exercises.get("items", []):
            new_tc = []
            seen = set()
            for tc in item.get("tests_concepts", []):
                if not tc.startswith("concept:"):
                    new_tc.append(tc)
                    continue

                if tc in REMOVE_SET:
                    changes["removed"] += 1
                    continue

                if tc in MERGE_MAP:
                    tc = MERGE_MAP[tc]
                    changes["merged"] += 1

                if tc not in seen:
                    seen.add(tc)
                    new_tc.append(tc)

            item["tests_concepts"] = new_tc

    if not dry_run and (changes["merged"] or changes["removed"]):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return changes


def main():
    dry_run = "--dry-run" in sys.argv

    files = sorted(
        f for f in glob.glob("data/ncert_biology_*.json")
        if ".raw." not in f and ".progress." not in f
    )

    print(f"\n🔧 Deduplicating concepts in {len(files)} biology files {'(DRY RUN)' if dry_run else ''}...\n")

    total = {"merged": 0, "removed": 0}

    for fp in files:
        changes = process_file(fp, dry_run)
        any_change = changes["merged"] or changes["removed"]

        if any_change:
            parts = []
            if changes["merged"]:
                parts.append(f"{changes['merged']} merged")
                total["merged"] += changes["merged"]
            if changes["removed"]:
                parts.append(f"{changes['removed']} removed")
                total["removed"] += changes["removed"]
            print(f"  ✏️  {fp.split('/')[-1]}: {', '.join(parts)}")
        else:
            print(f"  ✅ {fp.split('/')[-1]}: clean")

    print(f"\n📊 Total: {total}")
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
