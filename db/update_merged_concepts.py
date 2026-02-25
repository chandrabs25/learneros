"""
Update Neo4j to reflect merged/deduped concepts.

For each merge mapping:
1. Find the old Concept node
2. Move all REQUIRES/TESTS relationships to the canonical Concept node
3. Delete the old (orphaned) Concept node

Also removes any Concept nodes that have zero relationships.

Usage:
    uv run python db/update_merged_concepts.py
    uv run python db/update_merged_concepts.py --dry-run
"""

import os
import sys

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# All merge mappings from both physics and biology dedup scripts
MERGE_MAP = {
    # Physics
    "concept:amperes_circuital_law": "concept:amperes_law",
    "concept:work_and_energy": "concept:work",
    "concept:linear_momentum": "concept:momentum",
    "concept:charge_conservation_in_circuits": "concept:conservation_of_charge",
    "concept:p_n_junction_v_i_characteristics": "concept:p_n_junction",
    "concept:elasticity_modulus": "concept:elasticity",
    "concept:shear_stress_and_strain": "concept:stress_and_strain",
    "concept:uniform_circular_motion": "concept:circular_motion",

    # Biology
    "concept:aerobic_and_anaerobic_respiration": "concept:aerobic_respiration",
    "concept:whittakers_five_kingdom_classification": "concept:five_kingdom_classification",
    "concept:animal_kingdom_classification": "concept:animal_classification",
    "concept:cell_division_organelles": "concept:cell_organelles",
    "concept:cell_organelles_chloroplasts_and_mitochondria": "concept:cell_organelles",
    "concept:eukaryotic_cell_structure": "concept:cell_structure",
    "concept:plant_cell_structure": "concept:cell_structure",
    "concept:eukaryotic_cell": "concept:cell_structure",
    "concept:dna_and_rna_structure": "concept:dna_structure",
    "concept:dna_structure_and_replication": "concept:dna_replication",
    "concept:embryo_development": "concept:embryonic_development",
    "concept:pregnancy_and_embryonic_development": "concept:embryonic_development",
    "concept:genetics_and_inheritance": "concept:genetics",
    "concept:principles_of_inheritance_and_variation": "concept:inheritance",
    "concept:human_reproductive_system": "concept:reproductive_system",
    "concept:autonomic_nervous_system": "concept:human_nervous_system",
    "concept:human_excretory_system": "concept:excretory_system",
    "concept:unicellular_vs_multicellular": "concept:unicellular_and_multicellular_organisms",
    "concept:specialized_connective_tissues_bone_and_cartilage": "concept:connective_tissue",
    "concept:plant_anatomy_parenchyma_stomata_and_lenticels": "concept:plant_anatomy",
    "concept:open_circulatory_system": "concept:circulatory_system",
    "concept:evolutionary_history": "concept:evolution",
    "concept:plant_hormones": "concept:plant_growth_regulators",
    "concept:structure_of_pollen_grain_and_embryo_sac": "concept:embryo_sac_structure",
    "concept:vertebrate_classification": "concept:vertebrata",
}

# Concepts that were removed entirely
REMOVE_SET = {
    "concept:protoplasm",
    "concept:plumule",
    "concept:radula",
    "concept:stomochord",
    "concept:zygote",
    "concept:visible_spectrum_vibgyor",
    "concept:redox_potential_scale",
    "concept:pressure_gradients",
    "concept:states_of_matter",
    "concept:potential_energy",
}


def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


def run_merge(session, dry_run: bool):
    """Merge old concept nodes into canonical ones."""
    merged = 0
    for old_id, new_id in MERGE_MAP.items():
        # Check if old concept exists
        result = session.run(
            "MATCH (c:Concept {id: $id}) RETURN c.id AS id",
            id=old_id
        )
        if not result.single():
            continue

        print(f"  🔀 {old_id} → {new_id}")

        if dry_run:
            merged += 1
            continue

        # Ensure canonical concept exists
        session.run(
            """
            MERGE (c:Concept {id: $id})
            ON CREATE SET c.name = $name
            """,
            id=new_id,
            name=new_id.replace("concept:", "").replace("_", " ").title(),
        )

        # Move REQUIRES relationships (Section → Concept)
        session.run(
            """
            MATCH (s:Section)-[r:REQUIRES]->(old:Concept {id: $old_id})
            MATCH (new:Concept {id: $new_id})
            WHERE NOT (s)-[:REQUIRES]->(new)
            CREATE (s)-[:REQUIRES]->(new)
            DELETE r
            """,
            old_id=old_id, new_id=new_id,
        )
        # Delete any remaining duplicate REQUIRES
        session.run(
            "MATCH (s:Section)-[r:REQUIRES]->(old:Concept {id: $old_id}) DELETE r",
            old_id=old_id,
        )

        # Move TESTS relationships (Exercise → Concept)
        session.run(
            """
            MATCH (e:Exercise)-[r:TESTS]->(old:Concept {id: $old_id})
            MATCH (new:Concept {id: $new_id})
            WHERE NOT (e)-[:TESTS]->(new)
            CREATE (e)-[:TESTS]->(new)
            DELETE r
            """,
            old_id=old_id, new_id=new_id,
        )
        session.run(
            "MATCH (e:Exercise)-[r:TESTS]->(old:Concept {id: $old_id}) DELETE r",
            old_id=old_id,
        )

        # Delete the old concept node (now orphaned)
        session.run("MATCH (c:Concept {id: $id}) DELETE c", id=old_id)
        merged += 1

    return merged


def run_remove(session, dry_run: bool):
    """Remove concepts that were deleted entirely."""
    removed = 0
    for concept_id in REMOVE_SET:
        result = session.run(
            "MATCH (c:Concept {id: $id}) RETURN c.id AS id",
            id=concept_id
        )
        if not result.single():
            continue

        print(f"  🗑️  {concept_id}")
        if not dry_run:
            # Delete relationships first, then node
            session.run(
                "MATCH (c:Concept {id: $id}) DETACH DELETE c",
                id=concept_id,
            )
        removed += 1

    return removed


def cleanup_orphans(session, dry_run: bool):
    """Remove Concept nodes with zero relationships."""
    result = session.run(
        """
        MATCH (c:Concept)
        WHERE NOT (c)--()
        RETURN c.id AS id
        """
    )
    orphans = [r["id"] for r in result]

    if not orphans:
        return 0

    for oid in orphans:
        print(f"  🧹 orphan: {oid}")

    if not dry_run:
        session.run("MATCH (c:Concept) WHERE NOT (c)--() DELETE c")

    return len(orphans)


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"\n🔧 Updating Neo4j concepts {'(DRY RUN)' if dry_run else ''}\n")

    driver = get_driver()
    with driver.session() as session:
        print("Step 1: Merging renamed concepts...")
        merged = run_merge(session, dry_run)
        print(f"  → {merged} merged\n")

        print("Step 2: Removing deleted concepts...")
        removed = run_remove(session, dry_run)
        print(f"  → {removed} removed\n")

        print("Step 3: Cleaning orphaned concept nodes...")
        orphans = cleanup_orphans(session, dry_run)
        print(f"  → {orphans} orphans cleaned\n")

    driver.close()

    print(f"{'='*50}")
    print(f"✅ Done! Merged: {merged}, Removed: {removed}, Orphans: {orphans}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
