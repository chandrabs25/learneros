"""
Normalize chemistry JSON concept references.

This script:
1. Builds a comprehensive merge map for duplicate/similar concepts
2. Aligns chemistry concept names with physics conventions where applicable
3. Applies the merge map across all chemistry JSON files
4. Reports changes made
"""

import json
import glob
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("data")

# =============================================================================
# MERGE MAP: old_concept → canonical_concept
# Groups derived from automated near-duplicate detection + manual review
# =============================================================================

MERGE_MAP = {
    # --- Align with physics naming conventions ---
    "concept:hybridisation": "concept:hybridization",
    "concept:hybridisation_sp_sp_2_sp_3": "concept:hybridization",
    "concept:hybridisation_sp2": "concept:hybridization",
    "concept:hybridisation_sp3": "concept:hybridization",
    "concept:hybridisation_sp3d": "concept:hybridization",
    "concept:hybridisation_sp3d2": "concept:hybridization",
    "concept:hybridizaton": "concept:hybridization",
    "concept:hybridization_sp_3_sp_2": "concept:hybridization",
    "concept:hybridization_and_molecular_geometry": "concept:hybridization",
    "concept:sp3_hybridization": "concept:hybridization",
    "concept:faradays_law": "concept:faradays_laws",
    "concept:internal_energy": "concept:internal_energy",
    "concept:first_law_of_thermodynamics": "concept:first_law_of_thermodynamics",
    "concept:plancks_constant": "concept:plancks_constant",
    "concept:quantum_mechanics": "concept:quantum_mechanics",
    "concept:quantization": "concept:quantization_of_energy",
    "concept:states_of_matter": "concept:states_of_matter",
    "concept:homogeneous_mixtures_and_basic_states_of_matter": "concept:states_of_matter",
    "concept:wheatstone_bridge": "concept:wheatstone_bridge",
    "concept:work_function": "concept:work_function",
    "concept:photoelectric_effect": "concept:photoelectric_effect",
    "concept:photon_energy": "concept:photon_energy",

    # --- Singular/plural normalization (prefer singular or most common) ---
    "concept:oxidation_states": "concept:oxidation_state",
    "concept:oxidation_state_stability": "concept:oxidation_state",
    "concept:oxidation_state_trends": "concept:oxidation_state",
    "concept:lanthanoid_oxidation_states": "concept:oxidation_state",
    "concept:stability_of_oxidation_states": "concept:oxidation_state",
    "concept:oxidation_number_method": "concept:oxidation_number",
    "concept:pi_bonds": "concept:pi_bond",
    "concept:sigma_bonds": "concept:sigma_bond",
    "concept:sigma_electrons": "concept:sigma_bond",
    "concept:sigma_pi_bonds": "concept:pi_bond",
    "concept:grignard_reagents": "concept:grignard_reagent",
    "concept:lone_pairs": "concept:lone_pair",
    "concept:lewis_symbols": "concept:lewis_dot_symbols",
    "concept:galvanic_cells": "concept:galvanic_cell",
    "concept:galvanic_cell_representation": "concept:galvanic_cell",

    # --- Oxidation/Reduction consolidation ---
    "concept:oxidation": "concept:redox_reactions",
    "concept:oxidation_and_reduction": "concept:redox_reactions",
    "concept:oxidation_reduction": "concept:redox_reactions",
    "concept:redox_reactions_and_oxidation_states": "concept:redox_reactions",
    "concept:redox_reactions_in_terms_of_electron_transfer": "concept:redox_reactions",
    "concept:redox_behavior": "concept:redox_reactions",
    "concept:periodic_trends_in_redox": "concept:redox_reactions",
    "concept:stoichiometry_in_redox": "concept:stoichiometry",
    "concept:water_purification_redox": "concept:redox_reactions",
    "concept:redox_identification": "concept:redox_reactions",

    # --- Oxidising/reducing agents ---
    "concept:oxidising_agents": "concept:oxidising_agent",
    "concept:oxidizing_agents": "concept:oxidising_agent",
    "concept:oxidizing_property": "concept:oxidising_agent",
    "concept:oxidising_action": "concept:oxidising_agent",
    "concept:oxidising_strength_comparison": "concept:oxidising_strength",
    "concept:reducing_power_order": "concept:reducing_power",

    # --- Electronic configuration ---
    "concept:electronic_configurations": "concept:electronic_configuration",
    "concept:electronic_configuration_of_atoms": "concept:electronic_configuration",
    "concept:electronic_configuration_of_silver": "concept:electronic_configuration",
    "concept:electronic_configuration_principles": "concept:electronic_configuration",
    "concept:electronic_configuration_stability": "concept:electronic_configuration",

    # --- Electrode potential consolidation ---
    "concept:electrode_potential_measurement": "concept:electrode_potential",
    "concept:ph_and_electrode_potential": "concept:electrode_potential",
    "concept:standard_electrode_potential_table": "concept:standard_electrode_potential",
    "concept:standard_electrode_potentials": "concept:standard_electrode_potential",
    "concept:standard_cell_potential": "concept:standard_electrode_potential",

    # --- Electrochemical cells ---
    "concept:electrochemical_relations": "concept:electrochemical_cells",
    "concept:electrode_reactions": "concept:electrochemical_cells",
    "concept:stoichiometry_of_electrode_reactions": "concept:electrochemical_cells",

    # --- Bonding consolidation ---
    "concept:chemical_bond": "concept:chemical_bonding",
    "concept:covalent_bonding": "concept:covalent_bond",
    "concept:ionic_bonding": "concept:ionic_bond",
    "concept:polar_covalent_bond": "concept:covalent_bond",
    "concept:hydrogen_bond": "concept:hydrogen_bonding",
    "concept:intermolecular_hydrogen_bonding": "concept:hydrogen_bonding",

    # --- Resonance ---
    "concept:resonance_effect": "concept:resonance",
    "concept:resonance_stabilization": "concept:resonance",

    # --- Gibbs energy ---
    "concept:gibbs_free_energy": "concept:gibbs_energy",
    "concept:gibbs_energy_and_equilibrium": "concept:gibbs_energy",
    "concept:standard_gibbs_energy": "concept:gibbs_energy",
    "concept:thermodynamics_feasibility_of_reactions_and_gibbs_free_energy": "concept:gibbs_energy",
    "concept:feasibility_of_reaction": "concept:gibbs_energy",
    "concept:reaction_feasibility": "concept:gibbs_energy",

    # --- Thermodynamics ---
    "concept:thermodynamics": "concept:thermodynamic_systems",
    "concept:enthalpy_internal_energy_relation": "concept:internal_energy",
    "concept:work_and_heat": "concept:first_law_of_thermodynamics",
    "concept:reversible_work": "concept:first_law_of_thermodynamics",
    "concept:heat": "concept:heat_transfer",
    "concept:heat_capacity": "concept:molar_heat_capacity",
    "concept:state_function": "concept:state_function",
    "concept:entropy_change_of_surroundings": "concept:entropy",

    # --- Enthalpy ---
    "concept:enthalpy_change": "concept:enthalpy_of_formation",
    "concept:entropy_change": "concept:entropy",
    "concept:standard_enthalpy_of_formation": "concept:enthalpy_of_formation",

    # --- Chemical equilibrium ---
    "concept:chemical_equilibrium_and_ka": "concept:chemical_equilibrium",
    "concept:chemical_equilibrium_extent_of_reactions": "concept:chemical_equilibrium",

    # --- Kinetics ---
    "concept:first_order_kinetics": "concept:order_of_reaction",
    "concept:first_order_half_life": "concept:half_life",
    "concept:rate_law": "concept:rate_law",
    "concept:integrated_rate_law": "concept:rate_law",
    "concept:rate_law_application": "concept:rate_law",
    "concept:rate_law_determination": "concept:rate_law",
    "concept:rate_constant_units": "concept:rate_constant",
    "concept:order_of_a_reaction": "concept:order_of_reaction",
    "concept:reaction_rate_calculation": "concept:rate_of_reaction",

    # --- Concentration ---
    "concept:concentration_change": "concept:concentration",
    "concept:concentration_dependence": "concept:concentration",

    # --- Molar conductivity ---
    "concept:limiting_molar_conductivity": "concept:molar_conductivity",

    # --- Solutions ---
    "concept:depression_of_freezing_point": "concept:depression_in_freezing_point",
    "concept:deviations_from_raoults_law": "concept:raoults_law",
    "concept:relative_lowering_of_vapour_pressure": "concept:vapour_pressure_lowering",
    "concept:vapour_pressure": "concept:vapour_pressure_lowering",
    "concept:mole_fraction_in_vapour_phase": "concept:mole_fraction",
    "concept:gas_solubility": "concept:solubility",
    "concept:solubility_of_amines": "concept:solubility",
    "concept:ideal_solution": "concept:raoults_law",
    "concept:non_ideal_solutions": "concept:raoults_law",

    # --- Molar mass / Mole concept ---
    "concept:molar_mass_determination": "concept:molar_mass",
    "concept:mole_concept_and_basic_stoichiometry": "concept:mole_concept",
    "concept:empirical_and_molecular_formulas": "concept:molecular_formula",

    # --- Periodic table ---
    "concept:modern_periodic_table_structure": "concept:periodic_table",
    "concept:periodic_table_structure": "concept:periodic_table",
    "concept:periodic_table_application": "concept:periodic_table",
    "concept:periodic_table_organisation": "concept:periodic_table",
    "concept:periodic_table_position": "concept:periodic_table",
    "concept:periodic_table_blocks": "concept:periodic_table",
    "concept:periodic_table_blocks_s_p_d_f": "concept:periodic_table",
    "concept:metallic_character_trends": "concept:metallic_character",
    "concept:non_metallic_character_trends": "concept:non_metallic_character",

    # --- Quantum numbers ---
    "concept:principal_quantum_number": "concept:quantum_numbers",
    "concept:subshells": "concept:quantum_numbers",
    "concept:subshell_capacity": "concept:quantum_numbers",

    # --- Atomic structure ---
    "concept:sub_atomic_particles": "concept:atomic_structure",
    "concept:charge_quantization": "concept:quantization_of_energy",
    "concept:rutherford_scattering_experiment": "concept:atomic_structure",
    "concept:speed_of_light": "concept:electromagnetic_radiation",
    "concept:wave_nature_of_light": "concept:electromagnetic_radiation",

    # --- Named reactions consolidation ---
    "concept:named_reactions_in_amine_chemistry": "concept:named_reactions",

    # --- Isomerism ---
    "concept:structural_isomerism": "concept:isomerism",
    "concept:geometrical_isomerism": "concept:isomerism",
    "concept:optical_isomerism": "concept:isomerism",
    "concept:isomerism_in_alkanes": "concept:isomerism",
    "concept:isomerism_in_amines": "concept:isomerism",
    "concept:stereochemistry": "concept:isomerism",

    # --- Coordination chemistry ---
    "concept:coordination_entity": "concept:coordination_entities",
    "concept:ligand_strength": "concept:ligand_field_strength",
    "concept:square_planar_geometry": "concept:square_planar_complexes",

    # --- Valence bond theory ---
    "concept:vsepr_model": "concept:vsepr_theory",
    "concept:molecular_geometry": "concept:vsepr_theory",

    # --- Organic chemistry consolidation ---
    "concept:organic_structures": "concept:organic_compounds",
    "concept:structural_representation": "concept:structural_formulas",
    "concept:organic_reaction_types": "concept:types_of_organic_reactions",
    "concept:reaction_intermediates": "concept:reactive_intermediates",
    "concept:reaction_mechanisms": "concept:reaction_mechanism",
    "concept:dehydration_mechanism": "concept:reaction_mechanism",
    "concept:mechanism": "concept:reaction_mechanism",
    "concept:markovnikovs_rule": "concept:markovnikov_rule",
    "concept:reaction_with_nitrous_acid": "concept:reactions_with_nitrous_acid",

    # --- Identification ---
    "concept:identification": "concept:identification_of_compounds",
    "concept:identification_of_intermediates": "concept:identification_of_compounds",

    # --- Disproportionation ---
    "concept:disproportionation_reactions": "concept:disproportionation",
    "concept:disproportionation_balancing": "concept:disproportionation",

    # --- Protein structure ---
    "concept:protein_primary_structure": "concept:protein_structure",
    "concept:protein_secondary_structure": "concept:protein_structure",
    "concept:fibrous_proteins": "concept:protein_structure",
    "concept:protein_denaturation_effect": "concept:protein_denaturation",

    # --- Temperature ---
    "concept:temperature_dependence": "concept:temperature_effect",

    # --- Electron gain/ionization enthalpy ---
    "concept:electron_gain_enthalpy_trends": "concept:electron_gain_enthalpy",
    "concept:successive_electron_gain_enthalpy": "concept:electron_gain_enthalpy",
    "concept:ionisation_enthalpy": "concept:ionization_enthalpy",
    "concept:successive_ionization_enthalpies": "concept:ionization_enthalpy",
    "concept:successive_ionization_enthalpy": "concept:ionization_enthalpy",

    # --- Starch ---
    "concept:starch_structure": "concept:starch",

    # --- Vitamins (consolidate to one) ---
    "concept:vitamin_a": "concept:vitamins",
    "concept:vitamin_c": "concept:vitamins",
    "concept:vitamin_k": "concept:vitamins",
    "concept:vitamin_classification": "concept:vitamins",
    "concept:vitamin_solubility": "concept:vitamins",

    # --- Nucleic acids ---
    "concept:nucleoside": "concept:nucleotide",
    "concept:rna_structure": "concept:nucleic_acids",
    "concept:rna_types": "concept:nucleic_acids",
    "concept:pentose_sugars": "concept:nucleic_acids",

    # --- Miscellaneous consolidation ---
    "concept:colored_compounds": "concept:color_of_complexes",
    "concept:chemical_reactivity_trends": "concept:chemical_reactivity",
    "concept:preparation_of_compounds": "concept:organic_synthesis",
    "concept:ether_synthesis_limitations": "concept:williamson_ether_synthesis",
    "concept:williamson_ether_synthesis_limitations": "concept:williamson_ether_synthesis",
    "concept:surface": "concept:surface_chemistry",
    "concept:solid_state": "concept:states_of_matter",
    "concept:effective_nuclear_charge": "concept:nuclear_charge",
    "concept:shielding_effect": "concept:nuclear_charge",
    "concept:physical_properties_of_haloarenes": "concept:physical_properties",
    "concept:classification_of_halides": "concept:classification_of_amines",
    "concept:complex_compounds": "concept:coordination_compounds",
    "concept:daltons_law_of_partial_pressures": "concept:partial_pressure",
    "concept:degree_of_dissociation": "concept:dissociation",
    "concept:electrochemical_series": "concept:standard_electrode_potential",
    "concept:enthalpy_of_combustion": "concept:enthalpy_of_atomisation",
    "concept:enthalpy_of_vaporisation": "concept:enthalpy_of_atomisation",
    "concept:lactose_hydrolysis": "concept:carbohydrate_hydrolysis",
    "concept:sucrose_hydrolysis": "concept:carbohydrate_hydrolysis",
    "concept:pre_exponential_factor": "concept:arrhenius_equation",
    "concept:collision_theory": "concept:arrhenius_equation",
    "concept:stopping_potential": "concept:photoelectric_effect",
    "concept:wave_particle_duality": "concept:de_broglie_wavelength",
    "concept:rydberg_formula": "concept:bohr_model",
    "concept:paschen_series": "concept:bohr_model",
    "concept:balmer_series": "concept:bohr_model",
    "concept:lyman_series": "concept:bohr_model",
}


def normalize_ref(ref: str) -> str:
    """Apply merge map and basic normalization."""
    ref = ref.strip()
    # Apply merge map
    if ref in MERGE_MAP:
        return MERGE_MAP[ref]
    return ref


def process_file(filepath: str) -> dict:
    """Normalize all concept references in a single JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    changes = {"prereqs": 0, "exercises": 0, "deduped_prereqs": 0, "deduped_exercises": 0}
    ch = data["chapter"]

    # Normalize section prerequisites
    for sec in ch.get("sections", []):
        new_prereqs = []
        seen = set()
        for prereq in sec.get("prerequisites", []):
            if prereq.get("type") == "concept":
                old = prereq["ref"]
                prereq["ref"] = normalize_ref(old)
                if prereq["ref"] != old:
                    changes["prereqs"] += 1

            key = (prereq.get("type"), prereq.get("ref"))
            if key not in seen:
                seen.add(key)
                new_prereqs.append(prereq)
            else:
                changes["deduped_prereqs"] += 1
        sec["prerequisites"] = new_prereqs

    # Normalize exercise tests_concepts
    ex_data = ch.get("exercises")
    if ex_data:
        for item in ex_data.get("items", []):
            old_tcs = item.get("tests_concepts", [])
            new_tcs = []
            seen = set()
            for tc in old_tcs:
                if tc.startswith("concept:"):
                    new_tc = normalize_ref(tc)
                    if new_tc != tc:
                        changes["exercises"] += 1
                    tc = new_tc
                if tc not in seen:
                    seen.add(tc)
                    new_tcs.append(tc)
                else:
                    changes["deduped_exercises"] += 1
            item["tests_concepts"] = new_tcs

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return changes


def main():
    files = sorted(DATA_DIR.glob("ncert_chemistry_*.json"))
    if not files:
        print("No chemistry JSON files found")
        return

    print(f"\n🔧 Normalizing concepts in {len(files)} chemistry files...\n")

    total = {"prereqs": 0, "exercises": 0, "deduped_prereqs": 0, "deduped_exercises": 0}

    for fp in files:
        changes = process_file(str(fp))
        n = sum(changes.values())
        if n > 0:
            print(f"  ✏️  {fp.name}: {changes}")
        else:
            print(f"  ✅ {fp.name}: no changes needed")
        for k in total:
            total[k] += changes[k]

    print(f"\n📊 Total: {total}")
    print(f"   Prereq refs renamed: {total['prereqs']}")
    print(f"   Exercise refs renamed: {total['exercises']}")
    print(f"   Duplicate prereqs removed: {total['deduped_prereqs']}")
    print(f"   Duplicate exercise refs removed: {total['deduped_exercises']}")

    # Count final unique concepts
    all_concepts = set()
    for fp in files:
        with open(fp) as f:
            data = json.load(f)
        ch = data["chapter"]
        for sec in ch.get("sections", []):
            for p in sec.get("prerequisites", []):
                if p.get("type") == "concept":
                    all_concepts.add(p["ref"])
        ex = ch.get("exercises")
        if ex:
            for item in ex.get("items", []):
                for tc in item.get("tests_concepts", []):
                    if tc.startswith("concept:"):
                        all_concepts.add(tc)

    print(f"\n   Unique concepts after normalization: {len(all_concepts)} (was 694)")
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
