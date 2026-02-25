"""
Aggressive concept normalization — Phase 2.

Rolls up hyper-specific concepts into broader topic-level concepts,
matching the granularity of physics JSON files (~6-10 concepts per chapter).

Target: bring 511 → ~150-200 unique concepts.
"""

import json
import glob
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("data")

# =============================================================================
# PHASE 2 MERGE MAP: roll up specific concepts → broader topics
# =============================================================================

MERGE_MAP_V2 = {
    # =============================================
    # NOMENCLATURE — roll all IUPAC/naming variants into one
    # =============================================
    "concept:basic_iupac_nomenclature": "concept:iupac_nomenclature",
    "concept:iupac_naming": "concept:iupac_nomenclature",
    "concept:common_nomenclature": "concept:iupac_nomenclature",
    "concept:nomenclature": "concept:iupac_nomenclature",
    "concept:iupac_nomenclature_of_alcohols": "concept:iupac_nomenclature",
    "concept:iupac_nomenclature_of_cyclic_alcohols": "concept:iupac_nomenclature",
    "concept:iupac_nomenclature_of_unsaturated_alcohols": "concept:iupac_nomenclature",
    "concept:iupac_nomenclature_of_carboxylic_acids": "concept:iupac_nomenclature",
    "concept:iupac_nomenclature_of_alkanes": "concept:iupac_nomenclature",
    "concept:nomenclature_of_elements": "concept:iupac_nomenclature",
    "concept:formula_writing": "concept:iupac_nomenclature",

    # =============================================
    # ORGANIC REACTIONS — consolidate sub-types
    # =============================================
    "concept:nucleophilic_substitution_mechanisms_sn1_and_sn2": "concept:nucleophilic_substitution",
    "concept:nucleophilic_substitution_reactions": "concept:nucleophilic_substitution",
    "concept:sn2_reaction": "concept:nucleophilic_substitution",
    "concept:sn2_mechanism": "concept:nucleophilic_substitution",
    "concept:ambident_nucleophiles": "concept:nucleophilic_substitution",
    "concept:nucleophiles": "concept:nucleophilic_substitution",
    "concept:nucleophilicity_vs_basicity": "concept:nucleophilic_substitution",

    "concept:substitution_vs_elimination": "concept:elimination_reactions",
    "concept:zaitsev_rule": "concept:elimination_reactions",

    "concept:electrophilic_aromatic_substitution": "concept:electrophilic_substitution",
    "concept:electrophilic_substitution_in_aniline": "concept:electrophilic_substitution",
    "concept:friedel_crafts_acylation": "concept:electrophilic_substitution",
    "concept:aromatic_substitution": "concept:electrophilic_substitution",

    "concept:wurtz_reaction": "concept:named_reactions",
    "concept:finkelstein_reaction": "concept:named_reactions",
    "concept:aldol_condensation": "concept:named_reactions",
    "concept:cross_aldol_condensation": "concept:named_reactions",
    "concept:cannizzaro_reaction": "concept:named_reactions",
    "concept:clemmensen_reduction": "concept:named_reactions",
    "concept:etard_reaction": "concept:named_reactions",
    "concept:williamson_ether_synthesis": "concept:named_reactions",
    "concept:gabriel_phthalimide_synthesis": "concept:named_reactions",
    "concept:gabriel_synthesis": "concept:named_reactions",
    "concept:hoffmann_bromamide_degradation": "concept:named_reactions",
    "concept:hofmann_degradation": "concept:named_reactions",
    "concept:iodoform_test": "concept:named_reactions",
    "concept:ozonolysis": "concept:named_reactions",
    "concept:hydroboration_oxidation": "concept:named_reactions",
    "concept:lucas_reagent": "concept:named_reactions",

    "concept:aromatic_conversions": "concept:organic_conversions",
    "concept:reaction_sequences": "concept:organic_conversions",
    "concept:step_up_and_step_down_reactions": "concept:organic_conversions",
    "concept:organic_synthesis": "concept:organic_conversions",

    # =============================================
    # ORGANIC COMPOUND CLASSES
    # =============================================
    "concept:alcohol_oxidation": "concept:alcohols",
    "concept:alcohol_reactions": "concept:alcohols",
    "concept:alcohol_synthesis_from_alkenes": "concept:alcohols",
    "concept:classification_alcohols": "concept:alcohols",
    "concept:classification_allylic_alcohols": "concept:alcohols",
    "concept:reaction_of_alcohols": "concept:alcohols",
    "concept:primary_secondary_tertiary": "concept:alcohols",
    "concept:phenol_acidity": "concept:phenols",
    "concept:phenol_reactions": "concept:phenols",
    "concept:preparation_of_phenol": "concept:phenols",
    "concept:oxidation_of_alcohols": "concept:alcohols",

    "concept:ether_cleavage_by_hi": "concept:ethers",
    "concept:ether_cleavage_mechanism": "concept:ethers",
    "concept:ether_nomenclature": "concept:ethers",
    "concept:ether_synthesis_mechanism": "concept:ethers",
    "concept:anisole_reactions": "concept:ethers",

    "concept:preparation_of_haloalkanes": "concept:haloalkanes",
    "concept:reactions_of_haloalkanes": "concept:haloalkanes",
    "concept:polyhalogen_compounds": "concept:haloalkanes",
    "concept:allylic_substitution": "concept:haloalkanes",
    "concept:organometallic_compounds": "concept:haloalkanes",
    "concept:classification_of_amines": "concept:haloalkanes",

    "concept:carbonyl_group_polarity": "concept:carbonyl_compounds",
    "concept:carbonyl_derivatives": "concept:carbonyl_compounds",
    "concept:nucleophilic_addition": "concept:carbonyl_compounds",
    "concept:nucleophilic_acyl_substitution": "concept:carbonyl_compounds",
    "concept:alpha_hydrogen": "concept:carbonyl_compounds",
    "concept:ketone_synthesis_from_acyl_chlorides": "concept:carbonyl_compounds",
    "concept:oxidation_of_ketones": "concept:carbonyl_compounds",
    "concept:selective_reduction": "concept:carbonyl_compounds",
    "concept:hydration_of_alkynes": "concept:carbonyl_compounds",

    "concept:acid_strength": "concept:acidity",
    "concept:substituent_effects_on_acidity": "concept:acidity",

    "concept:alkylation_of_amines": "concept:amines",
    "concept:ammonia_structure": "concept:amines",
    "concept:basic_strength_of_amines": "concept:basicity_of_amines",
    "concept:basicity_trends": "concept:basicity_of_amines",
    "concept:boiling_point_of_amines": "concept:amines",
    "concept:reactions_of_amines": "concept:amines",
    "concept:reactions_with_nitrous_acid": "concept:amines",
    "concept:reduction_of_functional_groups": "concept:amines",
    "concept:identification_of_amines": "concept:amines",
    "concept:quaternary_ammonium_salts": "concept:amines",
    "concept:structure_of_ammonia": "concept:amines",
    "concept:salt_formation": "concept:amines",
    "concept:hinsbergs_test": "concept:amines",
    "concept:acylation": "concept:amines",
    "concept:benzoylation": "concept:amines",

    "concept:diazonium_reactions": "concept:diazonium_salts",
    "concept:diazonium_salt_applications": "concept:diazonium_salts",
    "concept:stability_of_diazonium_salts": "concept:diazonium_salts",

    # =============================================
    # ORGANIC GENERAL
    # =============================================
    "concept:organic_compounds": "concept:organic_chemistry",
    "concept:organic_functional_groups_aldehydes_ketones_and_alcohols": "concept:functional_groups",
    "concept:types_of_organic_reactions": "concept:reaction_mechanism",
    "concept:reactive_intermediates": "concept:reaction_mechanism",
    "concept:free_radicals": "concept:reaction_mechanism",
    "concept:carbocation_rearrangement": "concept:reaction_mechanism",
    "concept:free_radical_halogenation": "concept:reaction_mechanism",
    "concept:catalysis": "concept:reaction_mechanism",
    "concept:reagents": "concept:organic_conversions",
    "concept:hydration": "concept:organic_conversions",
    "concept:halogenation": "concept:reaction_mechanism",

    "concept:chemical_tests": "concept:identification_of_compounds",
    "concept:tollens_reagent": "concept:identification_of_compounds",
    "concept:tollens_test": "concept:identification_of_compounds",
    "concept:tollens_vs_fehlings": "concept:identification_of_compounds",
    "concept:reactivity_comparison": "concept:identification_of_compounds",

    "concept:purification_of_organic_compounds": "concept:purification_techniques",
    "concept:steam_distillation": "concept:purification_techniques",
    "concept:sublimation": "concept:purification_techniques",
    "concept:immiscibility": "concept:purification_techniques",
    "concept:distillation": "concept:purification_techniques",

    "concept:elemental_analysis": "concept:quantitative_analysis",
    "concept:qualitative_analysis": "concept:quantitative_analysis",
    "concept:sulphur_detection": "concept:quantitative_analysis",

    "concept:structural_formulas": "concept:iupac_nomenclature",
    "concept:isomers": "concept:isomerism",

    # =============================================
    # PHYSICAL CHEMISTRY
    # =============================================
    "concept:galvanic_cell": "concept:electrochemical_cells",
    "concept:standard_hydrogen_electrode": "concept:standard_electrode_potential",
    "concept:products_of_electrolysis": "concept:electrolysis",
    "concept:reactivity_series": "concept:standard_electrode_potential",
    "concept:logarithms": "concept:nernst_equation",
    "concept:ohms_law": "concept:molar_conductivity",
    "concept:conductivity": "concept:molar_conductivity",

    "concept:ppm": "concept:concentration",
    "concept:molality": "concept:concentration",
    "concept:molarity": "concept:concentration",
    "concept:stp": "concept:concentration",
    "concept:like_dissolves_like": "concept:solubility",
    "concept:molecular_interactions": "concept:solubility",
    "concept:solubility_product": "concept:solubility",
    "concept:solutions": "concept:solubility",
    "concept:osmotic_pressure": "concept:colligative_properties",
    "concept:depression_in_freezing_point": "concept:colligative_properties",
    "concept:elevation_in_boiling_point": "concept:colligative_properties",
    "concept:vapour_pressure_lowering": "concept:colligative_properties",
    "concept:vant_hoff_factor": "concept:colligative_properties",
    "concept:mole_fraction": "concept:concentration",
    "concept:abnormal_molar_mass": "concept:colligative_properties",

    "concept:rate_of_reaction": "concept:chemical_kinetics",
    "concept:rate_law": "concept:chemical_kinetics",
    "concept:rate_constant": "concept:chemical_kinetics",
    "concept:order_of_reaction": "concept:chemical_kinetics",
    "concept:half_life": "concept:chemical_kinetics",
    "concept:method_of_initial_rates": "concept:chemical_kinetics",
    "concept:kinetics": "concept:chemical_kinetics",
    "concept:activation_energy": "concept:arrhenius_equation",
    "concept:catalyst_mechanisms": "concept:arrhenius_equation",
    "concept:kinetic_theory_of_gases": "concept:chemical_kinetics",
    "concept:radioactive_decay": "concept:chemical_kinetics",

    "concept:thermodynamic_systems": "concept:thermodynamics",
    "concept:internal_energy": "concept:thermodynamics",
    "concept:internal_energy_change": "concept:thermodynamics",
    "concept:state_function": "concept:thermodynamics",
    "concept:phase_change": "concept:thermodynamics",
    "concept:isolated_system": "concept:thermodynamics",
    "concept:heat_transfer": "concept:thermodynamics",
    "concept:spontaneity": "concept:gibbs_energy",
    "concept:thermodynamic_stability": "concept:gibbs_energy",
    "concept:entropy": "concept:gibbs_energy",

    "concept:enthalpy_of_formation": "concept:enthalpy",
    "concept:enthalpy_of_atomisation": "concept:enthalpy",
    "concept:molar_heat_capacity": "concept:enthalpy",
    "concept:hess_law": "concept:enthalpy",
    "concept:bond_enthalpy": "concept:enthalpy",
    "concept:lattice_enthalpy": "concept:enthalpy",
    "concept:borns_haber_cycle": "concept:enthalpy",

    "concept:le_chateliers_principle": "concept:chemical_equilibrium",
    "concept:equilibrium_constant": "concept:chemical_equilibrium",
    "concept:dissociation": "concept:chemical_equilibrium",
    "concept:partial_pressure": "concept:chemical_equilibrium",

    # =============================================
    # INORGANIC CHEMISTRY
    # =============================================
    "concept:coordination_entities": "concept:coordination_compounds",
    "concept:coordination_number": "concept:coordination_compounds",
    "concept:definitions_in_coordination_chemistry": "concept:coordination_compounds",
    "concept:double_salts_vs_coordination_complexes": "concept:coordination_compounds",
    "concept:types_of_ligands": "concept:coordination_compounds",
    "concept:ligand_types_unidentate_and_didentate": "concept:coordination_compounds",
    "concept:chelating_ligands": "concept:coordination_compounds",
    "concept:chelate_effect": "concept:coordination_compounds",
    "concept:ionization_of_complexes": "concept:coordination_compounds",
    "concept:ligand_exchange": "concept:coordination_compounds",
    "concept:werners_theory": "concept:coordination_compounds",
    "concept:applications_of_coordination_compounds": "concept:coordination_compounds",
    "concept:complex_stability": "concept:coordination_compounds",
    "concept:metal_carbonyls": "concept:coordination_compounds",
    "concept:synergic_bonding": "concept:coordination_compounds",
    "concept:inner_outer_orbital_complexes": "concept:coordination_compounds",

    "concept:crystal_field_splitting_energy": "concept:crystal_field_theory",
    "concept:octahedral_splitting": "concept:crystal_field_theory",
    "concept:high_spin_vs_low_spin": "concept:crystal_field_theory",
    "concept:colour_in_coordination_compounds": "concept:crystal_field_theory",
    "concept:color_of_complexes": "concept:crystal_field_theory",
    "concept:d_d_transition": "concept:crystal_field_theory",
    "concept:absorption_spectra": "concept:crystal_field_theory",
    "concept:spectrochemical_series": "concept:crystal_field_theory",
    "concept:ligand_field_strength": "concept:crystal_field_theory",
    "concept:square_planar_complexes": "concept:crystal_field_theory",

    "concept:transition_elements_definition": "concept:transition_metals",
    "concept:transition_series_comparison": "concept:transition_metals",
    "concept:oxidising_agent": "concept:transition_metals",
    "concept:reducing_agent": "concept:transition_metals",
    "concept:oxidising_strength": "concept:transition_metals",
    "concept:reducing_power": "concept:transition_metals",
    "concept:potassium_dichromate": "concept:transition_metals",
    "concept:potassium_permanganate_preparation": "concept:transition_metals",
    "concept:permanganate_oxidation": "concept:transition_metals",
    "concept:interstitial_compounds": "concept:transition_metals",
    "concept:spin_only_formula": "concept:magnetic_properties",
    "concept:paramagnetism": "concept:magnetic_properties",
    "concept:unpaired_electrons": "concept:magnetic_properties",
    "concept:magnetic_moment": "concept:magnetic_properties",
    "concept:stability_in_aqueous_solution": "concept:transition_metals",
    "concept:ph_effect": "concept:transition_metals",

    "concept:inner_transition_elements": "concept:lanthanoids_actinoids",
    "concept:lanthanoid_contraction": "concept:lanthanoids_actinoids",
    "concept:lanthanoid_uses": "concept:lanthanoids_actinoids",
    "concept:lanthanoids_vs_actinoids": "concept:lanthanoids_actinoids",
    "concept:actinoid_properties": "concept:lanthanoids_actinoids",

    "concept:periodic_trends": "concept:periodic_table",
    "concept:modern_periodic_law": "concept:periodic_table",
    "concept:mendeleevs_periodic_law": "concept:periodic_table",
    "concept:metallic_character": "concept:periodic_table",
    "concept:non_metallic_character": "concept:periodic_table",
    "concept:metals_and_non_metals": "concept:periodic_table",
    "concept:noble_gas_configuration": "concept:periodic_table",
    "concept:valence_electrons": "concept:periodic_table",
    "concept:valency": "concept:periodic_table",
    "concept:p_block_elements": "concept:periodic_table",
    "concept:s_block_elements": "concept:periodic_table",
    "concept:nuclear_charge": "concept:periodic_table",

    # =============================================
    # ATOMIC STRUCTURE
    # =============================================
    "concept:sub_atomic_particles": "concept:atomic_structure",
    "concept:millikans_experiment": "concept:atomic_structure",
    "concept:neutron_diffraction": "concept:atomic_structure",
    "concept:electron_discovery": "concept:atomic_structure",
    "concept:cathode_rays": "concept:atomic_structure",
    "concept:laws_of_chemical_combination": "concept:atomic_structure",
    "concept:atomic_mass": "concept:atomic_structure",
    "concept:ionization_energy": "concept:ionization_enthalpy",
    "concept:kinetic_energy": "concept:atomic_structure",
    "concept:laser_power": "concept:atomic_structure",

    "concept:quantum_numbers": "concept:quantum_model",
    "concept:orbital_energies": "concept:quantum_model",
    "concept:orbital_wave_function": "concept:quantum_model",
    "concept:electronic_configuration": "concept:quantum_model",
    "concept:aufbau_principle": "concept:quantum_model",
    "concept:hunds_rule": "concept:quantum_model",
    "concept:pauli_exclusion_principle": "concept:quantum_model",

    "concept:bohr_model": "concept:atomic_spectra",
    "concept:bohr_atom_energy": "concept:atomic_spectra",
    "concept:de_broglie_wavelength": "concept:atomic_spectra",
    "concept:electromagnetic_radiation": "concept:atomic_spectra",
    "concept:quantization_of_energy": "concept:atomic_spectra",
    "concept:photoelectric_effect": "concept:atomic_spectra",
    "concept:photon_energy": "concept:atomic_spectra",

    # =============================================
    # CHEMICAL BONDING
    # =============================================
    "concept:chemical_bonding": "concept:chemical_bond",
    "concept:ionic_bond": "concept:chemical_bond",
    "concept:covalent_bond": "concept:chemical_bond",
    "concept:sigma_bond": "concept:chemical_bond",
    "concept:pi_bond": "concept:chemical_bond",
    "concept:lone_pair": "concept:chemical_bond",
    "concept:lewis_dot_symbols": "concept:chemical_bond",
    "concept:octet_rule": "concept:chemical_bond",
    "concept:ionic_character": "concept:chemical_bond",
    "concept:dipole_moment": "concept:chemical_bond",
    "concept:metallic_bonding": "concept:chemical_bond",

    "concept:molecular_orbital_types": "concept:molecular_orbital_theory",
    "concept:molecular_orbital_energy_levels": "concept:molecular_orbital_theory",
    "concept:bond_order": "concept:molecular_orbital_theory",

    "concept:physical_properties": "concept:intermolecular_forces",
    "concept:boiling_point": "concept:intermolecular_forces",
    "concept:boiling_points": "concept:intermolecular_forces",
    "concept:boiling_point_trends": "concept:intermolecular_forces",
    "concept:molecular_mass_effect": "concept:intermolecular_forces",
    "concept:branching_effect": "concept:intermolecular_forces",
    "concept:hydrophobic_and_hydrophilic_interactions": "concept:intermolecular_forces",
    "concept:surface_chemistry": "concept:intermolecular_forces",

    # =============================================
    # BIOMOLECULES
    # =============================================
    "concept:carbohydrate_hydrolysis": "concept:carbohydrates",
    "concept:carbohydrate_structure": "concept:carbohydrates",
    "concept:glucose_reactions": "concept:carbohydrates",
    "concept:glucose_structure": "concept:carbohydrates",
    "concept:fructose_structure": "concept:carbohydrates",
    "concept:cyclic_hemiacetal_structure": "concept:carbohydrates",
    "concept:disaccharides": "concept:carbohydrates",
    "concept:polysaccharides": "concept:carbohydrates",
    "concept:glycosidic_linkage": "concept:carbohydrates",
    "concept:optical_activity_and_chirality": "concept:carbohydrates",
    "concept:starch": "concept:carbohydrates",
    "concept:cellulose": "concept:carbohydrates",

    "concept:amino_acids": "concept:proteins",
    "concept:protein_structure": "concept:proteins",
    "concept:protein_denaturation": "concept:proteins",
    "concept:peptide_linkage": "concept:proteins",
    "concept:non_essential_amino_acids": "concept:proteins",
    "concept:fibrous_and_globular_proteins": "concept:proteins",

    "concept:nucleotide": "concept:nucleic_acids",
    "concept:nucleotide_hydrolysis": "concept:nucleic_acids",
    "concept:nucleic_acids_functions": "concept:nucleic_acids",
    "concept:dna_double_helix": "concept:nucleic_acids",
    "concept:phosphoric_acid": "concept:nucleic_acids",
    "concept:pentose_sugars": "concept:nucleic_acids",

    "concept:enzyme_catalysis": "concept:enzymes",

    # =============================================
    # REDOX
    # =============================================
    "concept:disproportionation": "concept:redox_reactions",
    "concept:oxidation_state": "concept:redox_reactions",
    "concept:oxidation_number": "concept:redox_reactions",
    "concept:thiosulphate_redox": "concept:redox_reactions",
    "concept:oxidising_power_of_halogens": "concept:redox_reactions",
    "concept:identifying_redox_species": "concept:redox_reactions",
    "concept:metal_displacement_series": "concept:redox_reactions",
    "concept:limiting_reagent": "concept:stoichiometry",
    "concept:balanced_equation_method": "concept:stoichiometry",

    # =============================================
    # MISC
    # =============================================
    "concept:molar_mass": "concept:mole_concept",
    "concept:molecular_formula": "concept:mole_concept",
    "concept:temperature_effect": "concept:arrhenius_equation",
    "concept:temperature": "concept:arrhenius_equation",
    "concept:xenon_chemistry": "concept:chemical_bond",
    "concept:chemical_reactivity": "concept:periodic_table",
    "concept:electron_gain_enthalpy": "concept:periodic_table",
    "concept:ionization_enthalpy": "concept:periodic_table",
    "concept:electronegativity": "concept:periodic_table",
    "concept:aliphatic_and_aromatic_hydrocarbons": "concept:hydrocarbons",
    "concept:tetravalence_of_carbon": "concept:organic_chemistry",
    "concept:inductive_effect": "concept:electronic_effects",
    "concept:resonance": "concept:electronic_effects",
    "concept:steric_hindrance": "concept:electronic_effects",
    "concept:hyperconjugation": "concept:electronic_effects",
    "concept:work_function": "concept:atomic_spectra",
    "concept:plancks_constant": "concept:atomic_spectra",
    "concept:speed_of_light": "concept:atomic_spectra",
}


def normalize_ref(ref: str) -> str:
    ref = ref.strip()
    if ref in MERGE_MAP_V2:
        return MERGE_MAP_V2[ref]
    return ref


def process_file(filepath: str) -> dict:
    with open(filepath) as f:
        data = json.load(f)

    changes = {"prereqs": 0, "exercises": 0, "deduped_prereqs": 0, "deduped_exercises": 0}
    ch = data["chapter"]

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

    ex_data = ch.get("exercises")
    if ex_data:
        for item in ex_data.get("items", []):
            old_tcs = item.get("tests", [])
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
            item["tests"] = new_tcs

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return changes


def main():
    files = sorted(DATA_DIR.glob("ncert_chemistry_*.json"))
    print(f"\n🔧 Phase 2: Aggressive concept compression on {len(files)} files...\n")

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

    # Count final unique concepts  
    all_concepts = set()
    per_chapter = {}
    for fp in files:
        with open(fp) as f:
            data = json.load(f)
        ch = data["chapter"]
        ch_concepts = set()
        for sec in ch.get("sections", []):
            for p in sec.get("prerequisites", []):
                if p.get("type") == "concept":
                    all_concepts.add(p["ref"])
                    ch_concepts.add(p["ref"])
        ex = ch.get("exercises")
        if ex:
            for item in ex.get("items", []):
                for tc in item.get("tests", []):
                    if tc.startswith("concept:"):
                        all_concepts.add(tc)
                        ch_concepts.add(tc)
        per_chapter[fp.name] = len(ch_concepts)

    print(f"\n   Unique concepts: {len(all_concepts)} (was 511, originally 694)")
    print(f"\n   Per chapter:")
    for fname, count in sorted(per_chapter.items()):
        print(f"     {fname}: {count} concepts")
    print(f"\n   Average: {sum(per_chapter.values())/len(per_chapter):.1f} concepts/chapter")
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
