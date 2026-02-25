"""
Fix ncert_chemistry_11_ch8.progress.json:
1. Remove the [SKIPPED] placeholder subsection from the last chunk
2. Populate exercises in the last chunk with 40 items (8.1-8.40) from txt file
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_11_ch8.progress.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    # =========================================================================
    # 1. Remove the SKIPPED placeholder from last chunk
    # =========================================================================
    last_chunk = data[-1]  # chunk 12 (index 12)
    sections = last_chunk["sections"]

    # Find the SUMMARY section with the skipped subsection
    summary_sec = next(s for s in sections if s["number"] == "SUMMARY")
    skipped_subs = [s for s in summary_sec["subsections"] if s.get("_skipped")]
    normal_subs = [s for s in summary_sec["subsections"] if not s.get("_skipped")]
    
    print(f"  Found {len(skipped_subs)} skipped subsection(s) to remove")
    summary_sec["subsections"] = normal_subs
    
    # If the summary section has no subsections left, remove it
    if not normal_subs:
        sections.remove(summary_sec)
        print("  Removed empty SUMMARY section from last chunk")
    
    # =========================================================================
    # 2. Populate exercises
    # =========================================================================
    exercises = [
        {
            "number": 1,
            "problem": "What are hybridisation states of each carbon atom in the following compounds? $CH_2=C=O$, $CH_3CH=CH_2$, $(CH_3)_2CO$, $CH_2=CHCN$, $C_6H_6$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:hybridisation"]
        },
        {
            "number": 2,
            "problem": "Indicate the $\\sigma$ and $\\pi$ bonds in the following molecules: $C_6H_6$, $C_6H_{12}$, $CH_2Cl_2$, $CH_2=C=CH_2$, $CH_3NO_2$, $HCONHCH_3$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:sigma_pi_bonds"]
        },
        {
            "number": 3,
            "problem": "Write bond line formulas for: Isopropyl alcohol, 2,3-Dimethylbutanal, Heptan-4-one.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "application",
            "tests": ["concept:bond_line_formulas"]
        },
        {
            "number": 4,
            "problem": "Give the IUPAC names of the following compounds: (a) (b) (c) (d) (e) (f) $Cl_2CHCH_2OH$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "application",
            "tests": ["concept:iupac_nomenclature"]
        },
        {
            "number": 5,
            "problem": "Which of the following represents the correct IUPAC name for the compounds concerned? (a) 2,2-Dimethylpentane or 2-Dimethylpentane (b) 2,4,7-Trimethyloctane or 2,5,7-Trimethyloctane (c) 2-Chloro-4-methylpentane or 4-Chloro-2-methylpentane (d) But-3-yn-1-ol or But-4-ol-1-yne.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:iupac_nomenclature"]
        },
        {
            "number": 6,
            "problem": "Draw formulas for the first five members of each homologous series beginning with the following compounds. (a) H-COOH (b) $CH_3COCH_3$ (c) $H-CH=CH_2$",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "application",
            "tests": ["concept:homologous_series"]
        },
        {
            "number": 7,
            "problem": "Give condensed and bond line structural formulas and identify the functional group(s) present, if any, for: (a) 2,2,4-Trimethylpentane (b) 2-Hydroxy-1,2,3-propanetricarboxylic acid (c) Hexanedial",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "application",
            "tests": ["concept:functional_groups", "concept:structural_formulas"]
        },
        {
            "number": 8,
            "problem": "Identify the functional groups in the following compounds (a) $CHO$ (b) (c) (d) $OCH_2CH_2N(C_2H_5)_2$ (e) (f) $CH_3CHO$",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:functional_groups"]
        },
        {
            "number": 9,
            "problem": "Which of the two: $O_2NCH_2CH_2O^-$ or $CH_3CH_2O^-$ is expected to be more stable and why?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:inductive_effect", "concept:stability_of_anions"]
        },
        {
            "number": 10,
            "problem": "Explain why alkyl groups act as electron donors when attached to a $\\pi$ system.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:hyperconjugation", "concept:inductive_effect"]
        },
        {
            "number": 11,
            "problem": "Draw the resonance structures for the following compounds. Show the electron shift using curved-arrow notation. (a) $C_6H_5OH$ (b) $C_6H_5NO_2$ (c) $CH_3CH=CHCHO$ (d) $C_6H_5$-$CHO$ (e) $C_6H_5$-$CH_2^+$ (f) $CH_3CH=CH$-$CH_2^+$",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "application",
            "tests": ["concept:resonance"]
        },
        {
            "number": 12,
            "problem": "What are electrophiles and nucleophiles? Explain with examples.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:electrophiles", "concept:nucleophiles"]
        },
        {
            "number": 13,
            "problem": "Identify the reagents shown in bold in the following equations as nucleophiles or electrophiles: (a) $CH_3COOH + HO^- \\rightarrow CH_3COO^- + H_2O$ (b) $CH_3COCH_3 + CN^- \\rightarrow (CH_3)_2C(CN)(OH)$ (c) $C_6H_6 + CH_3CO^+ \\rightarrow C_6H_5COCH_3$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "application",
            "tests": ["concept:electrophiles", "concept:nucleophiles"]
        },
        {
            "number": 14,
            "problem": "Classify the following reactions in one of the reaction type studied in this unit. (a) $CH_3CH_2Br + HS^- \\rightarrow CH_3CH_2SH + Br^-$ (b) $(CH_3)_2C=CH_2 + HCl \\rightarrow (CH_3)_2ClC$-$CH_3$ (c) $CH_3CH_2Br + HO^- \\rightarrow CH_2=CH_2 + H_2O + Br^-$ (d) $(CH_3)_3C$-$CH_2OH + HBr \\rightarrow (CH_3)_2CBrCH_2CH_3 + H_2O$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "application",
            "tests": ["concept:organic_reaction_types"]
        },
        {
            "number": 15,
            "problem": "What is the relationship between the members of following pairs of structures? Are they structural or geometrical isomers or resonance contributors? (a) $H_2C=C^+H$-$CH_2^-$ and $^-H_2C$-$CH=CH_2^+$ (b) $H_2C=C=CH_2$ and $H_2C$-$C \\equiv CH$ (c) $H_2C=C=O$ and $H_2C$-$C \\equiv O^+$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:isomerism", "concept:resonance"]
        },
        {
            "number": 16,
            "problem": "For the following bond cleavages, use curved-arrows to show the electron flow and classify each as homolysis or heterolysis. Identify reactive intermediate produced as free radical, carbocation and carbanion. (a) $CH_3O$-$OCH_3 \\rightarrow CH_3O^\\bullet + ^\\bullet OCH_3$ (b) $(CH_3)_3CO^- + H_2O \\rightarrow (CH_3)_3COH + ^-OH$ (c) Bromobenzene formation (d) $CH_2=CH_2 + H^+ \\rightarrow CH_3$-$CH_2^+$",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "application",
            "tests": ["concept:homolysis", "concept:heterolysis", "concept:reactive_intermediates"]
        },
        {
            "number": 17,
            "problem": "Explain the terms Inductive and Electromeric effects. Which electron displacement effect explains the following correct orders of acidity of the carboxylic acids? (a) $Cl_3CCOOH > Cl_2CHCOOH > ClCH_2COOH$ (b) $CH_3CH_2COOH > (CH_3)_2CHCOOH > (CH_3)_3C \\cdot COOH$",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:inductive_effect", "concept:electromeric_effect"]
        },
        {
            "number": 18,
            "problem": "Give a brief description of the principles of the following techniques taking an example in each case. (a) Crystallisation (b) Distillation (c) Chromatography",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:purification_techniques"]
        },
        {
            "number": 19,
            "problem": "Describe the method, which can be used to separate two compounds with different solubilities in a solvent S.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:crystallisation"]
        },
        {
            "number": 20,
            "problem": "What is the difference between distillation, distillation under reduced pressure and steam distillation?",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:distillation"]
        },
        {
            "number": 21,
            "problem": "Discuss the chemistry of Lassaigne's test.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:lassaigne_test"]
        },
        {
            "number": 22,
            "problem": "Differentiate between the principle of estimation of nitrogen in an organic compound by (i) Dumas method and (ii) Kjeldahl's method.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:dumas_method", "concept:kjeldahl_method"]
        },
        {
            "number": 23,
            "problem": "Discuss the principle of estimation of halogens, sulphur and phosphorus present in an organic compound.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:carius_method", "concept:quantitative_analysis"]
        },
        {
            "number": 24,
            "problem": "Explain the principle of paper chromatography.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:chromatography"]
        },
        {
            "number": 25,
            "problem": "Why is nitric acid added to sodium extract before adding silver nitrate for testing halogens?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:lassaigne_test", "concept:halogen_detection"]
        },
        {
            "number": 26,
            "problem": "Explain the reason for the fusion of an organic compound with metallic sodium for testing nitrogen, sulphur and halogens.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:lassaigne_test"]
        },
        {
            "number": 27,
            "problem": "Name a suitable technique of separation of the components from a mixture of calcium sulphate and camphor.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:sublimation"]
        },
        {
            "number": 28,
            "problem": "Explain, why an organic liquid vaporises at a temperature below its boiling point in its steam distillation?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:steam_distillation"]
        },
        {
            "number": 29,
            "problem": "Will $CCl_4$ give white precipitate of $AgCl$ on heating it with silver nitrate? Give reason for your answer.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:covalent_bonding", "concept:halogen_detection"]
        },
        {
            "number": 30,
            "problem": "Why is a solution of potassium hydroxide used to absorb carbon dioxide evolved during the estimation of carbon present in an organic compound?",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests": ["concept:quantitative_analysis"]
        },
        {
            "number": 31,
            "problem": "Why is it necessary to use acetic acid and not sulphuric acid for acidification of sodium extract for testing sulphur by lead acetate test?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests": ["concept:sulphur_detection"]
        },
        {
            "number": 32,
            "problem": "An organic compound contains 69% carbon and 4.8% hydrogen, the remainder being oxygen. Calculate the masses of carbon dioxide and water produced when 0.20 g of this substance is subjected to complete combustion.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests": ["concept:quantitative_analysis", "concept:combustion"]
        },
        {
            "number": 33,
            "problem": "A sample of 0.50 g of an organic compound was treated according to Kjeldahl's method. The ammonia evolved was absorbed in 50 ml of 0.5 M $H_2SO_4$. The residual acid required 60 mL of 0.5 M solution of NaOH for neutralisation. Find the percentage composition of nitrogen in the compound.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests": ["concept:kjeldahl_method"]
        },
        {
            "number": 34,
            "problem": "0.3780 g of an organic chloro compound gave 0.5740 g of silver chloride in Carius estimation. Calculate the percentage of chlorine present in the compound.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests": ["concept:carius_method"]
        },
        {
            "number": 35,
            "problem": "In the estimation of sulphur by Carius method, 0.468 g of an organic sulphur compound afforded 0.668 g of barium sulphate. Find out the percentage of sulphur in the given compound.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests": ["concept:carius_method"]
        },
        {
            "number": 36,
            "problem": "In the organic compound $CH_3$-$CH$-$CH_2$-$C \\equiv CH$, the pair of hybridised orbitals involved in the formation of $C_2$-$C_3$ bond is: (a) $sp$-$sp^2$ (b) $sp$-$sp^3$ (c) $sp^2$-$sp^3$ (d) $sp^3$-$sp^3$",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "mcq",
            "tests": ["concept:hybridisation"]
        },
        {
            "number": 37,
            "problem": "In the Lassaigne's test for nitrogen in an organic compound, the Prussian blue colour is obtained due to the formation of: (a) $Na_4[Fe(CN)_6]$ (b) $Fe_4[Fe(CN)_6]_3$ (c) $Fe_2[Fe(CN)_6]$ (d) $Fe_3[Fe(CN)_6]_4$",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "mcq",
            "tests": ["concept:lassaigne_test"]
        },
        {
            "number": 38,
            "problem": "Which of the following carbocation is most stable? (a) $(CH_3)_3C^+$ (b) $(CH_3)_3C^-$ (c) $(CH_3)_2CH_2^+$ (d) $(CH_3)_2CH_2^-$",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "mcq",
            "tests": ["concept:carbocation_stability", "concept:hyperconjugation"]
        },
        {
            "number": 39,
            "problem": "The best and latest technique for isolation, purification and separation of organic compounds is: (a) Crystallisation (b) Distillation (c) Sublimation (d) Chromatography",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "mcq",
            "tests": ["concept:purification_techniques"]
        },
        {
            "number": 40,
            "problem": "The reaction: $CH_3CH_2I + KOH(aq) \\rightarrow CH_3CH_2OH + KI$ is classified as: (a) electrophilic substitution (b) nucleophilic substitution (c) elimination (d) addition.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "mcq",
            "tests": ["concept:organic_reaction_types"]
        }
    ]

    # Populate exercises in the last chunk
    last_chunk["exercises"] = {
        "title": "Exercises",
        "items": exercises
    }
    print(f"  ✅ Added {len(exercises)} exercises to the last chunk")

    # Verify no [SKIPPED] markers remain
    json_str = json.dumps(data)
    assert "[SKIPPED" not in json_str, "ERROR: [SKIPPED] marker still present!"
    print("  ✅ No [SKIPPED] markers remain")

    # Save
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved fixed JSON to {JSON_PATH}")
    print(f"   File size: {JSON_PATH.stat().st_size:,} bytes")

    # Validate
    with open(JSON_PATH) as f:
        json.load(f)
    print("   JSON validation: ✅ valid")


if __name__ == "__main__":
    main()
