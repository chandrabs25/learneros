"""
Fix ncert_chemistry_12_ch1.json:
1. Remove the [SKIPPED] placeholder subsection from Summary
2. Add 37 end-of-chapter exercises (1.5-1.41) from the txt file
3. Clean up remaining [CONTINUES] marker
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch1.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Remove the SKIPPED placeholder from Summary section
    # =========================================================================
    for sec in ch["sections"]:
        if sec["number"] == "Summary":
            orig_len = len(sec["subsections"])
            sec["subsections"] = [
                s for s in sec["subsections"]
                if not s.get("_skipped") and "[SKIPPED" not in (s.get("title") or "")
            ]
            removed = orig_len - len(sec["subsections"])
            # Re-number
            for idx, sub in enumerate(sec["subsections"], 1):
                sub["order"] = idx
            print(f"  ✅ Removed {removed} skipped subsection(s) from Summary")
            # Clean [CONTINUES] from last subsection if present
            if sec["subsections"]:
                last = sec["subsections"][-1]
                if last.get("content_text", "").endswith("[CONTINUES]"):
                    last["content_text"] = last["content_text"][:-len("[CONTINUES]")].rstrip()
                    print("  ✅ Cleaned [CONTINUES] from Summary")
            break

    # =========================================================================
    # 2. Add end-of-chapter exercises (1.5-1.41 from txt file)
    # =========================================================================
    # The existing exercises are in-text questions numbered 1-12
    # We add the end-of-chapter exercises continuing the numbering
    new_exercises = [
        {
            "number": 13,
            "problem": "A solution of glucose in water is labelled as 10% w/w, what would be the molality and mole fraction of each component in the solution? If the density of solution is 1.2 g mL$^{-1}$, then what shall be the molarity of the solution?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molality", "concept:mole_fraction", "concept:molarity"]
        },
        {
            "number": 14,
            "problem": "How many mL of 0.1 M HCl are required to react completely with 1 g mixture of $Na_2CO_3$ and $NaHCO_3$ containing equimolar amounts of both?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molarity", "concept:stoichiometry"]
        },
        {
            "number": 15,
            "problem": "A solution is obtained by mixing 300 g of 25% solution and 400 g of 40% solution by mass. Calculate the mass percentage of the resulting solution.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:mass_percentage"]
        },
        {
            "number": 16,
            "problem": "An antifreeze solution is prepared from 222.6 g of ethylene glycol ($C_2H_6O_2$) and 200 g of water. Calculate the molality of the solution. If the density of the solution is 1.072 g mL$^{-1}$, then what shall be the molarity of the solution?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molality", "concept:molarity"]
        },
        {
            "number": 17,
            "problem": "A sample of drinking water was found to be severely contaminated with chloroform ($CHCl_3$) supposed to be a carcinogen. The level of contamination was 15 ppm (by mass): (i) express this in percent by mass (ii) determine the molality of chloroform in the water sample.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:ppm", "concept:molality"]
        },
        {
            "number": 18,
            "problem": "What role does the molecular interaction play in a solution of alcohol and water?",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:molecular_interactions", "concept:non_ideal_solutions"]
        },
        {
            "number": 19,
            "problem": "Why do gases always tend to be less soluble in liquids as the temperature is raised?",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:gas_solubility", "concept:temperature_effect"]
        },
        {
            "number": 20,
            "problem": "State Henry's law and mention some important applications.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:henrys_law"]
        },
        {
            "number": 21,
            "problem": "The partial pressure of ethane over a solution containing $6.56 \\times 10^{-3}$ g of ethane is 1 bar. If the solution contains $5.00 \\times 10^{-2}$ g of ethane, then what shall be the partial pressure of the gas?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:henrys_law"]
        },
        {
            "number": 22,
            "problem": "What is meant by positive and negative deviations from Raoult's law and how is the sign of $\\Delta_{mix}H$ related to positive and negative deviations from Raoult's law?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:raoults_law", "concept:deviations_from_raoults_law"]
        },
        {
            "number": 23,
            "problem": "An aqueous solution of 2% non-volatile solute exerts a pressure of 1.004 bar at the normal boiling point of the solvent. What is the molar mass of the solute?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:molar_mass"]
        },
        {
            "number": 24,
            "problem": "Heptane and octane form an ideal solution. At 373 K, the vapour pressures of the two liquid components are 105.2 kPa and 46.8 kPa respectively. What will be the vapour pressure of a mixture of 26.0 g of heptane and 35 g of octane?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:ideal_solution"]
        },
        {
            "number": 25,
            "problem": "The vapour pressure of water is 12.3 kPa at 300 K. Calculate vapour pressure of 1 molal solution of a non-volatile solute in it.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:vapour_pressure_lowering"]
        },
        {
            "number": 26,
            "problem": "Calculate the mass of a non-volatile solute (molar mass 40 g mol$^{-1}$) which should be dissolved in 114 g octane to reduce its vapour pressure to 80%.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:vapour_pressure_lowering"]
        },
        {
            "number": 27,
            "problem": "A solution containing 30 g of non-volatile solute exactly in 90 g of water has a vapour pressure of 2.8 kPa at 298 K. Further, 18 g of water is then added to the solution and the new vapour pressure becomes 2.9 kPa at 298 K. Calculate: (i) molar mass of the solute (ii) vapour pressure of water at 298 K.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:molar_mass"]
        },
        {
            "number": 28,
            "problem": "A 5% solution (by mass) of cane sugar in water has freezing point of 271K. Calculate the freezing point of 5% glucose in water if freezing point of pure water is 273.15 K.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:depression_in_freezing_point"]
        },
        {
            "number": 29,
            "problem": "Two elements A and B form compounds having formula $AB_2$ and $AB_4$. When dissolved in 20 g of benzene ($C_6H_6$), 1 g of $AB_2$ lowers the freezing point by 2.3 K whereas 1.0 g of $AB_4$ lowers it by 1.3 K. The molar depression constant for benzene is 5.1 K kg mol$^{-1}$. Calculate atomic masses of A and B.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:depression_in_freezing_point", "concept:molar_mass"]
        },
        {
            "number": 30,
            "problem": "At 300 K, 36 g of glucose present in a litre of its solution has an osmotic pressure of 4.98 bar. If the osmotic pressure of the solution is 1.52 bars at the same temperature, what would be its concentration?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:osmotic_pressure"]
        },
        {
            "number": 31,
            "problem": "Suggest the most important type of intermolecular attractive interaction in the following pairs. (i) n-hexane and n-octane (ii) $I_2$ and $CCl_4$ (iii) $NaClO_4$ and water (iv) methanol and acetone (v) acetonitrile ($CH_3CN$) and acetone ($C_3H_6O$).",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:intermolecular_forces"]
        },
        {
            "number": 32,
            "problem": "Based on solute-solvent interactions, arrange the following in order of increasing solubility in n-octane and explain. Cyclohexane, KCl, $CH_3OH$, $CH_3CN$.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:solubility", "concept:like_dissolves_like"]
        },
        {
            "number": 33,
            "problem": "Amongst the following compounds, identify which are insoluble, partially soluble and highly soluble in water? (i) phenol (ii) toluene (iii) formic acid (iv) ethylene glycol (v) chloroform (vi) pentanol.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:solubility"]
        },
        {
            "number": 34,
            "problem": "If the density of some lake water is 1.25 g mL$^{-1}$ and contains 92 g of $Na^+$ ions per kg of water, calculate the molarity of $Na^+$ ions in the lake.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molarity"]
        },
        {
            "number": 35,
            "problem": "If the solubility product of CuS is $6 \\times 10^{-16}$, calculate the maximum molarity of CuS in aqueous solution.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:solubility_product"]
        },
        {
            "number": 36,
            "problem": "Calculate the mass percentage of aspirin ($C_9H_8O_4$) in acetonitrile ($CH_3CN$) when 6.5 g of $C_9H_8O_4$ is dissolved in 450 g of $CH_3CN$.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:mass_percentage"]
        },
        {
            "number": 37,
            "problem": "Nalorphine ($C_{19}H_{21}NO_3$), similar to morphine, is used to combat withdrawal symptoms in narcotic users. Dose of nalorphine generally given is 1.5 mg. Calculate the mass of $1.5 \\times 10^{-3}$ m aqueous solution required for the above dose.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molality"]
        },
        {
            "number": 38,
            "problem": "Calculate the amount of benzoic acid ($C_6H_5COOH$) required for preparing 250 mL of 0.15 M solution in methanol.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molarity"]
        },
        {
            "number": 39,
            "problem": "The depression in freezing point of water observed for the same amount of acetic acid, trichloroacetic acid and trifluoroacetic acid increases in the order given above. Explain briefly.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:depression_in_freezing_point", "concept:dissociation"]
        },
        {
            "number": 40,
            "problem": "Calculate the depression in the freezing point of water when 10 g of $CH_3CH_2CHClCOOH$ is added to 250 g of water. $K_a = 1.4 \\times 10^{-3}$, $K_f = 1.86$ K kg mol$^{-1}$.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:depression_in_freezing_point", "concept:vant_hoff_factor"]
        },
        {
            "number": 41,
            "problem": "19.5 g of $CH_2FCOOH$ is dissolved in 500 g of water. The depression in the freezing point of water observed is 1.0°C. Calculate the van't Hoff factor and dissociation constant of fluoroacetic acid.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:vant_hoff_factor", "concept:dissociation_constant"]
        },
        {
            "number": 42,
            "problem": "Vapour pressure of water at 293 K is 17.535 mm Hg. Calculate the vapour pressure of water at 293 K when 25 g of glucose is dissolved in 450 g of water.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:vapour_pressure_lowering"]
        },
        {
            "number": 43,
            "problem": "Henry's law constant for the molality of methane in benzene at 298 K is $4.27 \\times 10^5$ mm Hg. Calculate the solubility of methane in benzene at 298 K under 760 mm Hg.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:henrys_law"]
        },
        {
            "number": 44,
            "problem": "100 g of liquid A (molar mass 140 g mol$^{-1}$) was dissolved in 1000 g of liquid B (molar mass 180 g mol$^{-1}$). The vapour pressure of pure liquid B was found to be 500 torr. Calculate the vapour pressure of pure liquid A and its vapour pressure in the solution if the total vapour pressure of the solution is 475 Torr.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:ideal_solution"]
        },
        {
            "number": 45,
            "problem": "Vapour pressures of pure acetone and chloroform at 328 K are 741.8 mm Hg and 632.8 mm Hg respectively. Assuming that they form ideal solution over the entire range of composition, plot $p_{total}$, $p_{chloroform}$, and $p_{acetone}$ as a function of $x_{acetone}$. The experimental data observed for different compositions of mixture is provided. Plot this data also on the same graph paper. Indicate whether it has positive deviation or negative deviation from the ideal solution.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:deviations_from_raoults_law"]
        },
        {
            "number": 46,
            "problem": "Benzene and toluene form ideal solution over the entire range of composition. The vapour pressure of pure benzene and toluene at 300 K are 50.71 mm Hg and 32.06 mm Hg respectively. Calculate the mole fraction of benzene in vapour phase if 80 g of benzene is mixed with 100 g of toluene.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:raoults_law", "concept:ideal_solution"]
        },
        {
            "number": 47,
            "problem": "The air is a mixture of a number of gases. The major components are oxygen and nitrogen with approximate proportion of 20% is to 79% by volume at 298 K. The water is in equilibrium with air at a pressure of 10 atm. At 298 K if the Henry's law constants for oxygen and nitrogen at 298 K are $3.30 \\times 10^7$ mm and $6.51 \\times 10^7$ mm respectively, calculate the composition of these gases in water.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:henrys_law"]
        },
        {
            "number": 48,
            "problem": "Determine the amount of $CaCl_2$ ($i = 2.47$) dissolved in 2.5 litre of water such that its osmotic pressure is 0.75 atm at 27°C.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:osmotic_pressure", "concept:vant_hoff_factor"]
        },
        {
            "number": 49,
            "problem": "Determine the osmotic pressure of a solution prepared by dissolving 25 mg of $K_2SO_4$ in 2 litre of water at 25°C, assuming that it is completely dissociated.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:osmotic_pressure", "concept:vant_hoff_factor"]
        }
    ]

    existing = ch["exercises"]["items"]
    existing.extend(new_exercises)
    print(f"  ✅ Added {len(new_exercises)} end-of-chapter exercises (total: {len(existing)})")

    # =========================================================================
    # 3. Verify
    # =========================================================================
    json_str = json.dumps(data)
    assert "[SKIPPED" not in json_str, "ERROR: [SKIPPED] marker still present!"
    print("  ✅ No [SKIPPED] markers remain")

    continues_count = json_str.count("[CONTINUES]")
    if continues_count:
        print(f"  ⚠️  {continues_count} [CONTINUES] markers remain")
    else:
        print("  ✅ No [CONTINUES] markers remain")

    # Save
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved fixed JSON to {JSON_PATH}")
    print(f"   File size: {JSON_PATH.stat().st_size:,} bytes")

    # Validate
    with open(JSON_PATH) as f:
        json.load(f)
    print("   JSON validation: ✅ valid")

    # Print exercise summary
    print(f"\n=== Exercises ===")
    print(f"   In-text (1-12): existing")
    print(f"   End-of-chapter (13-49): newly added from exercises 1.5-1.41")
    print(f"   Total: {len(existing)}")


if __name__ == "__main__":
    main()
