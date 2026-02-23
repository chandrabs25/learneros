"""
Fix ncert_chemistry_12_ch2.json:
1. Remove [SKIPPED] placeholder from section 2.8
2. Add missing in-text problems 2.13-2.15 as worked examples in section 2.8
3. Add Hydrogen Economy subsection to section 2.8  
4. Add Summary section
5. Add 18 end-of-chapter exercises (2.1-2.18)
6. Fix existing exercise numbering (21→1, 22→2, etc.)
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch2.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Fix section 2.8: remove SKIPPED, add missing content
    # =========================================================================
    sec_28 = next(s for s in ch["sections"] if s["number"] == "2.8")
    
    # Remove SKIPPED subsection
    sec_28["subsections"] = [
        s for s in sec_28["subsections"]
        if "[SKIPPED" not in (s.get("title") or "")
    ]
    print("  ✅ Removed SKIPPED subsection from 2.8")

    # Clean [CONTINUES] from last subsection
    if sec_28["subsections"]:
        last = sec_28["subsections"][-1]
        ct = last.get("content_text", "")
        if ct.endswith("[CONTINUES]"):
            last["content_text"] = ct[:-len("[CONTINUES]")].rstrip()

    # Add missing worked examples (in-text problems 2.13-2.15) to Prevention of Corrosion
    prevention_sub = next(
        (s for s in sec_28["subsections"] if "Prevention" in s.get("title", "")),
        None
    )
    if prevention_sub:
        prevention_sub.setdefault("worked_examples", []).extend([
            {
                "label": "Problem 2.13",
                "problem": "Write the chemistry of recharging the lead storage battery, highlighting all the materials that are involved during recharging.",
                "solution": "During recharging, the cell is operated as an electrolytic cell. The reactions are reversed: $PbSO_4$ at the anode is converted back to $PbO_2$ and $PbSO_4$ at the cathode is converted back to $Pb$. The overall recharging reaction is: $2PbSO_4(s) + 2H_2O(l) \\rightarrow Pb(s) + PbO_2(s) + 2H_2SO_4(aq)$. Materials involved: lead sulphate, water, lead, lead dioxide, and sulphuric acid."
            },
            {
                "label": "Problem 2.14",
                "problem": "Suggest two materials other than hydrogen that can be used as fuels in fuel cells.",
                "solution": "Methanol and methane can be used as fuels in fuel cells."
            },
            {
                "label": "Problem 2.15",
                "problem": "Explain how rusting of iron is envisaged as setting up of an electrochemical cell.",
                "solution": "During rusting, the iron surface acts as an anode where oxidation occurs: $Fe(s) \\rightarrow Fe^{2+}(aq) + 2e^-$. Another spot acts as a cathode where oxygen is reduced: $O_2(g) + 4H^+(aq) + 4e^- \\rightarrow 2H_2O(l)$. The $Fe^{2+}$ ions are further oxidised to $Fe^{3+}$ which form hydrated ferric oxide ($Fe_2O_3 \\cdot xH_2O$), i.e., rust."
            }
        ])
        print("  ✅ Added Problems 2.13-2.15 to Prevention of Corrosion")

    # Add Hydrogen Economy subsection
    max_order = max(s["order"] for s in sec_28["subsections"])
    sec_28["subsections"].append({
        "order": max_order + 1,
        "title": "The Hydrogen Economy",
        "content_text": (
            "At present the main source of energy driving our economy is fossil fuels such as "
            "coal, oil and gas. As more people aspire to improve their standard of living, "
            "energy requirements will increase. The per capita consumption of energy is a "
            "measure of development. Carbon dioxide produced by the combustion of fossil fuels "
            "results in the 'Greenhouse Effect', leading to a rise in Earth's surface temperature, "
            "causing polar ice to melt and ocean levels to rise. To avoid such a catastrophe, "
            "we need to limit our use of carbonaceous fuels. Hydrogen provides an ideal alternative "
            "as its combustion results in water only. Hydrogen production must come from splitting "
            "water using solar energy. Therefore, hydrogen can be used as a renewable and non-polluting "
            "source of energy — this is the vision of the Hydrogen Economy. Both the production of "
            "hydrogen by electrolysis of water and hydrogen combustion in a fuel cell are important "
            "technologies for the future, and both are based on electrochemical principles."
        ),
        "content_type": "explanation",
        "worked_examples": [],
        "diagrams": [],
        "tables": []
    })
    print("  ✅ Added Hydrogen Economy subsection")

    # =========================================================================
    # 2. Add Summary section
    # =========================================================================
    ch["sections"].append({
        "number": "Summary",
        "title": "Summary",
        "subsections": [
            {
                "order": 1,
                "title": "Electrochemical Cells and Potentials",
                "content_text": (
                    "An electrochemical cell consists of two metallic electrodes dipping in "
                    "electrolytic solution(s). Electrochemical cells are of two types: in a "
                    "galvanic cell, the chemical energy of a spontaneous redox reaction is "
                    "converted into electrical work; in an electrolytic cell, electrical energy "
                    "is used to carry out a non-spontaneous redox reaction. The standard electrode "
                    "potential is defined with respect to the standard hydrogen electrode (taken as "
                    "zero). The standard potential of the cell is obtained by: "
                    "$E_{cell}^\\circ = E^\\circ_{cathode} - E^\\circ_{anode}$. "
                    "Standard cell potentials are related to standard Gibbs energy "
                    "($\\Delta_r G^\\circ = -nFE_{cell}^\\circ$) and the equilibrium constant "
                    "($\\Delta_r G^\\circ = -RT \\ln K$). Concentration dependence of potentials "
                    "is given by the Nernst equation."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [],
                "tables": []
            },
            {
                "order": 2,
                "title": "Conductance and Electrolysis",
                "content_text": (
                    "The conductivity $\\kappa$ of an electrolytic solution depends on the "
                    "concentration of the electrolyte, nature of solvent and temperature. "
                    "Molar conductivity $\\Lambda_m = \\kappa / c$. Conductivity decreases but "
                    "molar conductivity increases with decrease in concentration. Kohlrausch's "
                    "law of independent migration of ions states that molar conductivity at "
                    "infinite dilution is the sum of contributions of individual ions. "
                    "Batteries and fuel cells are useful forms of galvanic cells. Corrosion of "
                    "metals is essentially an electrochemical phenomenon. Electrochemical "
                    "principles are relevant to the Hydrogen Economy."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [],
                "tables": []
            }
        ],
        "prerequisites": []
    })
    print("  ✅ Added Summary section")

    # =========================================================================
    # 3. Fix existing exercise numbering (21→1, 22→2, etc.)
    # =========================================================================
    existing_ex = ch.get("exercises", {}).get("items", [])
    for ex in existing_ex:
        old_num = ex["number"]
        # 21→1, 22→2, ..., 29→9, 210→10, 211→11, 212→12
        if old_num >= 21 and old_num <= 29:
            ex["number"] = old_num - 20
        elif old_num == 210:
            ex["number"] = 10
        elif old_num == 211:
            ex["number"] = 11
        elif old_num == 212:
            ex["number"] = 12
    print(f"  ✅ Fixed exercise numbering: {[ex['number'] for ex in existing_ex]}")

    # =========================================================================
    # 4. Add 18 end-of-chapter exercises (2.1-2.18 from txt)
    # =========================================================================
    new_exercises = [
        {
            "number": 13,
            "problem": "Arrange the following metals in the order in which they displace each other from the solution of their salts. Al, Cu, Fe, Mg and Zn.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:electrochemical_series"]
        },
        {
            "number": 14,
            "problem": "Given the standard electrode potentials, $K^+/K = -2.93$ V, $Ag^+/Ag = 0.80$ V, $Hg^{2+}/Hg = 0.79$ V, $Mg^{2+}/Mg = -2.37$ V, $Cr^{3+}/Cr = -0.74$ V. Arrange these metals in their increasing order of reducing power.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:standard_electrode_potential", "concept:reducing_power"]
        },
        {
            "number": 15,
            "problem": "Depict the galvanic cell in which the reaction $Zn(s) + 2Ag^+(aq) \\rightarrow Zn^{2+}(aq) + 2Ag(s)$ takes place. Further show: (i) Which of the electrode is negatively charged? (ii) The carriers of the current in the cell. (iii) Individual reaction at each electrode.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:galvanic_cell"]
        },
        {
            "number": 16,
            "problem": "Calculate the standard cell potentials of galvanic cell in which the following reactions take place: (i) $2Cr(s) + 3Cd^{2+}(aq) \\rightarrow 2Cr^{3+}(aq) + 3Cd$ (ii) $Fe^{2+}(aq) + Ag^+(aq) \\rightarrow Fe^{3+}(aq) + Ag(s)$. Calculate the $\\Delta_r G^\\circ$ and equilibrium constant of the reactions.",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:standard_cell_potential", "concept:gibbs_energy"]
        },
        {
            "number": 17,
            "problem": "Write the Nernst equation and emf of the following cells at 298 K: (i) $Mg(s)|Mg^{2+}(0.001M)||Cu^{2+}(0.0001 M)|Cu(s)$ (ii) $Fe(s)|Fe^{2+}(0.001M)||H^+(1M)|H_2(g)(1bar)|Pt(s)$ (iii) $Sn(s)|Sn^{2+}(0.050 M)||H^+(0.020 M)|H_2(g)(1 bar)|Pt(s)$ (iv) $Pt(s)|Br^-(0.010 M)|Br_2(l)||H^+(0.030 M)|H_2(g)(1 bar)|Pt(s)$",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:nernst_equation"]
        },
        {
            "number": 18,
            "problem": "In the button cells widely used in watches and other devices the following reaction takes place: $Zn(s) + Ag_2O(s) + H_2O(l) \\rightarrow Zn^{2+}(aq) + 2Ag(s) + 2OH^-(aq)$. Determine $\\Delta_r G^\\circ$ and $E^\\circ$ for the reaction.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:gibbs_energy", "concept:standard_cell_potential"]
        },
        {
            "number": 19,
            "problem": "Define conductivity and molar conductivity for the solution of an electrolyte. Discuss their variation with concentration.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:conductivity", "concept:molar_conductivity"]
        },
        {
            "number": 20,
            "problem": "The conductivity of 0.20 M solution of KCl at 298 K is 0.0248 S cm$^{-1}$. Calculate its molar conductivity.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molar_conductivity"]
        },
        {
            "number": 21,
            "problem": "The resistance of a conductivity cell containing 0.001 M KCl solution at 298 K is 1500 $\\Omega$. What is the cell constant if conductivity of 0.001 M KCl solution at 298 K is $0.146 \\times 10^{-3}$ S cm$^{-1}$.",
            "solution": None,
            "difficulty": "easy",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:cell_constant", "concept:conductivity"]
        },
        {
            "number": 22,
            "problem": "The conductivity of sodium chloride at 298 K has been determined at different concentrations. Calculate $\\Lambda_m$ for all concentrations and draw a plot between $\\Lambda_m$ and $c^{1/2}$. Find the value of $\\Lambda_m^\\circ$.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molar_conductivity", "concept:kohlrausch_law"]
        },
        {
            "number": 23,
            "problem": "Conductivity of 0.00241 M acetic acid is $7.896 \\times 10^{-5}$ S cm$^{-1}$. Calculate its molar conductivity. If $\\Lambda_m^\\circ$ for acetic acid is 390.5 S cm$^2$ mol$^{-1}$, what is its dissociation constant?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:molar_conductivity", "concept:dissociation_constant"]
        },
        {
            "number": 24,
            "problem": "How much charge is required for the following reductions: (i) 1 mol of $Al^{3+}$ to Al? (ii) 1 mol of $Cu^{2+}$ to Cu? (iii) 1 mol of $MnO_4^-$ to $Mn^{2+}$?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:faradays_law"]
        },
        {
            "number": 25,
            "problem": "How much electricity in terms of Faraday is required to produce (i) 20.0 g of Ca from molten $CaCl_2$? (ii) 40.0 g of Al from molten $Al_2O_3$?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:faradays_law"]
        },
        {
            "number": 26,
            "problem": "How much electricity is required in coulomb for the oxidation of (i) 1 mol of $H_2O$ to $O_2$? (ii) 1 mol of FeO to $Fe_2O_3$?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:faradays_law"]
        },
        {
            "number": 27,
            "problem": "A solution of $Ni(NO_3)_2$ is electrolysed between platinum electrodes using a current of 5 amperes for 20 minutes. What mass of Ni is deposited at the cathode?",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:electrolysis", "concept:faradays_law"]
        },
        {
            "number": 28,
            "problem": "Three electrolytic cells A, B, C containing solutions of $ZnSO_4$, $AgNO_3$ and $CuSO_4$, respectively are connected in series. A steady current of 1.5 amperes was passed through them until 1.45 g of silver deposited at the cathode of cell B. How long did the current flow? What mass of copper and zinc were deposited?",
            "solution": None,
            "difficulty": "hard",
            "exercise_type": "numerical",
            "tests_concepts": ["concept:electrolysis", "concept:faradays_law"]
        },
        {
            "number": 29,
            "problem": "Using the standard electrode potentials, predict if the reaction between the following is feasible: (i) $Fe^{3+}(aq)$ and $I^-(aq)$ (ii) $Ag^+(aq)$ and $Cu(s)$ (iii) $Fe^{3+}(aq)$ and $Br^-(aq)$ (iv) $Ag(s)$ and $Fe^{3+}(aq)$ (v) $Br_2(aq)$ and $Fe^{2+}(aq)$.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:standard_electrode_potential", "concept:feasibility_of_reaction"]
        },
        {
            "number": 30,
            "problem": "Predict the products of electrolysis in each of the following: (i) An aqueous solution of $AgNO_3$ with silver electrodes. (ii) An aqueous solution of $AgNO_3$ with platinum electrodes. (iii) A dilute solution of $H_2SO_4$ with platinum electrodes. (iv) An aqueous solution of $CuCl_2$ with platinum electrodes.",
            "solution": None,
            "difficulty": "medium",
            "exercise_type": "conceptual",
            "tests_concepts": ["concept:electrolysis", "concept:products_of_electrolysis"]
        }
    ]

    existing_ex.extend(new_exercises)
    print(f"  ✅ Added {len(new_exercises)} end-of-chapter exercises (total: {len(existing_ex)})")

    # =========================================================================
    # 5. Verify
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
    items = ch["exercises"]["items"]
    print(f"\n=== Exercises ({len(items)}) ===")
    print(f"   In-text (1-12): renumbered from 21-212")
    print(f"   End-of-chapter (13-30): newly added from exercises 2.1-2.18")


if __name__ == "__main__":
    main()
