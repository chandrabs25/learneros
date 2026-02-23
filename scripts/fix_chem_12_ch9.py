"""
Fix ncert_chemistry_12_ch9.json:
1. Fix 9.4 sub 10: replace SKIPPED with Hofmann worked example + Exercise 9.3
2. Add missing section 9.5 (Physical Properties)
3. Fix 9.6: add basic character intro (from txt) if not already present
4. Fix Summary: remove SKIPPED sub 6
5. Fix exercise numbering and add 5 exercises (9.10-9.14)
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch9.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Fix section 9.4 — replace SKIPPED sub 10 with proper content
    # =========================================================================
    sec_94 = next(s for s in ch["sections"] if s["number"] == "9.4")
    
    # Remove SKIPPED sub and replace with worked example
    sec_94["subsections"] = [
        s for s in sec_94["subsections"]
        if "[SKIPPED" not in (s.get("title") or "")
    ]
    
    # Clean [CONTINUES] from last sub
    if sec_94["subsections"]:
        last = sec_94["subsections"][-1]
        ct = last.get("content_text", "")
        if ct.endswith("[CONTINUES]"):
            last["content_text"] = ct[:-len("[CONTINUES]")].rstrip()
    
    # Add Hofmann worked example and Exercise 9.3
    sec_94["subsections"].append({
        "order": 10,
        "title": "Worked Example: Hofmann Bromamide Degradation",
        "content_text": "",
        "content_type": "application",
        "worked_examples": [
            {
                "label": "Example",
                "problem": "Write structures and IUPAC names of (i) the amide which gives propanamine by Hoffmann bromamide reaction. (ii) the amine produced by the Hoffmann degradation of benzamide.",
                "solution": "(i) Propanamine contains three carbons. Hence, the amide molecule must contain four carbon atoms. The starting amide is butanamide ($CH_3CH_2CH_2CONH_2$). (ii) Benzamide is an aromatic amide containing seven carbon atoms. The amine formed is aniline (benzenamine, $C_6H_5NH_2$), an aromatic primary amine containing six carbon atoms."
            }
        ],
        "diagrams": [],
        "tables": []
    })
    sec_94["subsections"].append({
        "order": 11,
        "title": "In-text Exercise 9.3",
        "content_text": "",
        "content_type": "application",
        "worked_examples": [
            {
                "label": "Exercise 9.3",
                "problem": "How will you convert (i) Benzene into aniline (ii) Benzene into N,N-dimethylaniline (iii) $Cl$-$(CH_2)_4$-$Cl$ into hexan-1,6-diamine?",
                "solution": None
            }
        ],
        "diagrams": [],
        "tables": []
    })
    
    # Renumber
    for idx, sub in enumerate(sec_94["subsections"], 1):
        sub["order"] = idx
    print(f"  ✅ Fixed 9.4: replaced SKIPPED, added Hofmann example + Exercise 9.3 ({len(sec_94['subsections'])} subs)")

    # =========================================================================
    # 2. Add missing section 9.5 (Physical Properties)
    # =========================================================================
    sections = ch["sections"]
    # Insert before 9.6
    insert_idx = next(i for i, s in enumerate(sections) if s["number"] == "9.6")
    
    sections.insert(insert_idx, {
        "number": "9.5",
        "title": "Physical Properties",
        "subsections": [
            {
                "order": 1,
                "title": "General Physical Properties",
                "content_text": (
                    "The lower aliphatic amines are gases with fishy odour. Primary amines with three or more carbon atoms "
                    "are liquid and still higher ones are solid. Aniline and other arylamines are usually colourless but get "
                    "coloured on storage due to atmospheric oxidation."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [],
                "tables": []
            },
            {
                "order": 2,
                "title": "Solubility",
                "content_text": (
                    "Lower aliphatic amines are soluble in water because they can form hydrogen bonds with water molecules. "
                    "However, solubility decreases with increase in molar mass of amines due to increase in size of the "
                    "hydrophobic alkyl part. Higher amines are essentially insoluble in water. Amines are soluble in organic "
                    "solvents like alcohol, ether and benzene. Alcohols are more polar than amines and form stronger "
                    "intermolecular hydrogen bonds than amines."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [],
                "tables": []
            },
            {
                "order": 3,
                "title": "Boiling Points and Hydrogen Bonding",
                "content_text": (
                    "Primary and secondary amines are engaged in intermolecular association due to hydrogen bonding between "
                    "nitrogen of one and hydrogen of another molecule. This intermolecular association is more in primary "
                    "amines than in secondary amines as there are two hydrogen atoms available for hydrogen bond formation. "
                    "Tertiary amines do not have intermolecular association due to the absence of hydrogen atom available "
                    "for hydrogen bond formation. Therefore, the order of boiling points of isomeric amines is: "
                    "Primary > Secondary > Tertiary."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [
                    {"title": "Intermolecular hydrogen bonding in primary amines", "description": "Diagram showing hydrogen bonding between the H atom of one primary amine molecule and the N atom of another, forming a chain: R-N-H···N-H···N-R."}
                ],
                "tables": [
                    {
                        "title": "Boiling Points of Some Compounds",
                        "headers": ["Compound", "Molar mass", "b.p./K"],
                        "rows": [
                            ["$n$-$C_4H_9NH_2$", "73", "350.8"],
                            ["$(C_2H_5)_2NH$", "73", "329.3"],
                            ["$C_2H_5N(CH_3)_2$", "73", "310.5"],
                            ["$C_2H_5CH(CH_3)_2$", "72", "300.8"],
                            ["$n$-$C_4H_9OH$", "74", "390.3"]
                        ]
                    }
                ]
            }
        ],
        "prerequisites": []
    })
    print("  ✅ Added section 9.5 (Physical Properties) with 3 subsections")

    # =========================================================================
    # 3. Check 9.6 — add basic character intro if missing
    # =========================================================================
    sec_96 = next(s for s in ch["sections"] if s["number"] == "9.6")
    
    # The txt shows the start of 9.6 (basic character, Kb/pKb, Table 9.3)
    # Check if 9.6 already has this content
    has_basic_intro = any(
        'basic character' in (sub.get('title','') + sub.get('content_text','')).lower()
        and 'reaction with acids' in sub.get('content_text','').lower()
        for sub in sec_96['subsections']
    )
    
    if not has_basic_intro:
        # Insert basic character intro at the beginning of 9.6
        new_sub = {
            "order": 0,
            "title": "Basic Character of Amines",
            "content_text": (
                "Amines are reactive due to the difference in electronegativity between nitrogen and hydrogen atoms and "
                "the presence of an unshared pair of electrons on the nitrogen atom. The number of hydrogen atoms attached "
                "to the nitrogen atom determines the course of reaction. Amines behave as nucleophiles due to the presence "
                "of the unshared electron pair.\n\n"
                "Amines, being basic in nature, react with acids to form salts: $RNH_2 + HX \\rightleftharpoons RNH_3^+X^-$. "
                "Amine salts on treatment with a base like NaOH regenerate the parent amine: "
                "$RNH_3^+X^- + OH^- \\rightarrow RNH_2 + H_2O + X^-$. "
                "Amine salts are soluble in water but insoluble in organic solvents like ether. "
                "This reaction is the basis for the separation of amines from non-basic organic compounds.\n\n"
                "Basic character of amines can be understood in terms of their $K_b$ and $pK_b$ values. "
                "Larger the value of $K_b$ or smaller the value of $pK_b$, stronger is the base. "
                "Aliphatic amines are stronger bases than ammonia ($pK_b = 4.75$) due to the +I effect of alkyl groups "
                "leading to high electron density on the nitrogen atom. Their $pK_b$ values lie in the range of 3 to 4.22. "
                "Aromatic amines are weaker bases than ammonia due to the electron withdrawing nature of the aryl group."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": [
                {
                    "title": "pKb Values of Amines in Aqueous Phase",
                    "headers": ["Name of amine", "pKb"],
                    "rows": [
                        ["Methanamine", "3.38"],
                        ["N-Methylmethanamine", "3.27"],
                        ["N,N-Dimethylmethanamine", "4.22"],
                        ["Ethanamine", "3.29"],
                        ["N-Ethylethanamine", "3.00"],
                        ["N,N-Diethylethanamine", "3.25"],
                        ["Benzenamine (Aniline)", "9.38"],
                        ["Phenylmethanamine", "4.70"],
                        ["N-Methylaniline", "9.30"],
                        ["N,N-Dimethylaniline", "8.92"]
                    ]
                }
            ]
        }
        sec_96["subsections"].insert(0, new_sub)
        # Renumber
        for idx, sub in enumerate(sec_96["subsections"], 1):
            sub["order"] = idx
        print(f"  ✅ Added basic character intro to 9.6 ({len(sec_96['subsections'])} subs)")
    else:
        print("  ℹ️  9.6 already has basic character content, skipping")

    # =========================================================================
    # 4. Fix Summary — remove SKIPPED sub 6
    # =========================================================================
    summ = next(s for s in ch["sections"] if s["number"] == "Summary")
    summ["subsections"] = [
        s for s in summ["subsections"]
        if "[SKIPPED" not in (s.get("title") or "")
    ]
    # Clean [CONTINUES] 
    if summ["subsections"]:
        last = summ["subsections"][-1]
        ct = last.get("content_text", "")
        if ct.endswith("[CONTINUES]"):
            last["content_text"] = ct[:-len("[CONTINUES]")].rstrip()
    for idx, sub in enumerate(summ["subsections"], 1):
        sub["order"] = idx
    print(f"  ✅ Removed SKIPPED from Summary ({len(summ['subsections'])} subs)")

    # =========================================================================
    # 5. Fix exercise numbering and add exercises
    # =========================================================================
    existing_ex = ch.get("exercises", {}).get("items", [])
    # Current: [1, 2, 94, 95, 96, 97, 98, 3, 4, 5, 6, 7, 8, 9] — renumber sequentially
    for idx, ex in enumerate(existing_ex, 1):
        ex["number"] = idx
    print(f"  ✅ Renumbered {len(existing_ex)} existing exercises (1-{len(existing_ex)})")

    # Add 5 end-of-chapter exercises (9.10-9.14)
    new_exercises = [
        {"number": 15, "problem": "An aromatic compound 'A' on treatment with aqueous ammonia and heating forms compound 'B' which on heating with $Br_2$ and KOH forms a compound 'C' of molecular formula $C_6H_7N$. Write the structures and IUPAC names of compounds A, B and C.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests_concepts": ["concept:hofmann_degradation", "concept:identification"]},
        {"number": 16, "problem": "Complete the following reactions: (i) $C_6H_5NH_2 + CHCl_3 + alc. KOH \\rightarrow$ (ii) $C_6H_5N_2Cl + H_3PO_2 + H_2O \\rightarrow$ (iii) $C_6H_5NH_2 + H_2SO_4 (conc.) \\rightarrow$ (iv) $C_6H_5N_2Cl + C_2H_5OH \\rightarrow$ (v) $C_6H_5NH_2 + Br_2 (aq) \\rightarrow$ (vi) $C_6H_5NH_2 + (CH_3CO)_2O \\rightarrow$ (vii) $C_6H_5N_2Cl \\xrightarrow{HBF_4, then NaNO_2/Cu}$", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests_concepts": ["concept:reactions_of_amines", "concept:diazonium_reactions"]},
        {"number": 17, "problem": "Why cannot aromatic primary amines be prepared by Gabriel phthalimide synthesis?", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests_concepts": ["concept:gabriel_synthesis"]},
        {"number": 18, "problem": "Write the reactions of (i) aromatic and (ii) aliphatic primary amines with nitrous acid.", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests_concepts": ["concept:reactions_with_nitrous_acid"]},
        {"number": 19, "problem": "Give plausible explanation for each of the following: (i) Why are amines less acidic than alcohols of comparable molecular masses? (ii) Why do primary amines have higher boiling point than tertiary amines? (iii) Why are aliphatic amines stronger bases than aromatic amines?", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests_concepts": ["concept:basicity_of_amines", "concept:physical_properties"]}
    ]

    existing_ex.extend(new_exercises)
    print(f"  ✅ Added {len(new_exercises)} end-of-chapter exercises (total: {len(existing_ex)})")

    # =========================================================================
    # 6. Clean markers
    # =========================================================================
    json_str = json.dumps(data)
    assert "[SKIPPED" not in json_str, "ERROR: [SKIPPED] still present!"
    print("  ✅ No [SKIPPED] markers remain")

    for sec in ch["sections"]:
        for sub in sec.get("subsections", []):
            ct = sub.get("content_text", "")
            if "[CONTINUES]" in ct:
                sub["content_text"] = ct.replace("[CONTINUES]", "").rstrip()

    json_str = json.dumps(data)
    print(f"  {'⚠️  ' + str(json_str.count('[CONTINUES]')) if '[CONTINUES]' in json_str else '✅ No'} [CONTINUES] markers remain")

    # Save
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved fixed JSON to {JSON_PATH}")
    print(f"   File size: {JSON_PATH.stat().st_size:,} bytes")

    with open(JSON_PATH) as f:
        json.load(f)
    print("   JSON validation: ✅ valid")

    print(f"\n=== Final Structure ===")
    for sec in ch["sections"]:
        n = len(sec.get("subsections", []))
        print(f"  {sec['number']}: {sec['title']} ({n} subs)")
    print(f"  Exercises: {len(existing_ex)}")


if __name__ == "__main__":
    main()
