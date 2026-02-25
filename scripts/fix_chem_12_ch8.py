"""
Fix ncert_chemistry_12_ch8.json:
1. Add ring substitution content to section 8.9.4
2. Add missing section 8.10 (Uses of Carboxylic Acids) - currently 8.10 is Intext Answers
3. Add Summary section
4. Fix exercise numbering and add 16 end-of-chapter exercises (8.1-8.16)
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch8.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Fix section 8.9.4 — add ring substitution to existing HVZ content
    # =========================================================================
    sec_894 = next(s for s in ch["sections"] if s["number"] == "8.9.4")
    
    # Clean SKIPPED and CONTINUES from existing sub
    sub1 = sec_894["subsections"][0]
    ct = sub1.get("content_text", "")
    ct = ct.replace("[SKIPPED — this content needs manual extraction from pages 28-30]", "").strip()
    ct = ct.replace("[CONTINUES]", "").strip()
    sub1["content_text"] = ct
    
    # Add ring substitution subsection
    sec_894["subsections"].append({
        "order": 2,
        "title": "Ring Substitution",
        "content_text": (
            "Aromatic carboxylic acids undergo electrophilic substitution reactions in which the carboxyl group acts "
            "as a deactivating and meta-directing group. They however, do not undergo Friedel-Crafts reaction "
            "(because the carboxyl group is deactivating and the catalyst aluminium chloride (Lewis acid) gets bonded "
            "to the carboxyl group). Examples include: (i) Nitration of benzoic acid with conc. $HNO_3$ and conc. "
            "$H_2SO_4$ yields m-nitrobenzoic acid. (ii) Bromination of benzoic acid with $Br_2/FeBr_3$ yields "
            "m-bromobenzoic acid."
        ),
        "content_type": "explanation",
        "worked_examples": [],
        "diagrams": [
            {"title": "Nitration of benzoic acid", "description": "Benzoic acid reacts with conc. HNO₃ and conc. H₂SO₄ to yield m-nitrobenzoic acid"},
            {"title": "Bromination of benzoic acid", "description": "Benzoic acid reacts with Br₂/FeBr₃ to yield m-bromobenzoic acid"}
        ],
        "tables": []
    })
    print("  ✅ Added ring substitution subsection to 8.9.4")

    # =========================================================================
    # 2. Add section: Uses of Carboxylic Acids (before current 8.10)
    # =========================================================================
    sections = ch["sections"]
    # Find current 8.10 and insert before it
    insert_idx = next(i for i, s in enumerate(sections) if s["number"] == "8.10")
    
    sections.insert(insert_idx, {
        "number": "8.10",
        "title": "Uses of Carboxylic Acids",
        "subsections": [
            {
                "order": 1,
                "title": "Industrial and Commercial Uses",
                "content_text": (
                    "Methanoic acid is used in rubber, textile, dyeing, leather and electroplating industries. "
                    "Ethanoic acid is used as solvent and as vinegar in food industry. Hexanedioic acid is used "
                    "in the manufacture of nylon-6,6. Esters of benzoic acid are used in perfumery. Sodium "
                    "benzoate is used as a food preservative. Higher fatty acids are used for the manufacture "
                    "of soaps and detergents."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [],
                "tables": []
            }
        ],
        "prerequisites": []
    })
    
    # Rename old 8.10 to 8.11
    old_810 = sections[insert_idx + 1]
    old_810["number"] = "8.11"
    print("  ✅ Added section 8.10 (Uses of Carboxylic Acids), renumbered old 8.10→8.11")

    # =========================================================================
    # 3. Add Summary section
    # =========================================================================
    has_summary = any(s["number"] == "Summary" for s in sections)
    if not has_summary:
        sections.append({
            "number": "Summary",
            "title": "Summary",
            "subsections": [
                {
                    "order": 1,
                    "title": "Aldehydes and Ketones",
                    "content_text": (
                        "Aldehydes, ketones and carboxylic acids are important classes of organic compounds containing the "
                        "carbonyl group. These are highly polar molecules and boil at higher temperatures than hydrocarbons "
                        "and weakly polar compounds of comparable molecular masses. Lower members are soluble in water due "
                        "to hydrogen bonding. Aldehydes are prepared by dehydrogenation or controlled oxidation of primary "
                        "alcohols and selective reduction of acyl halides. Aromatic aldehydes may be prepared by oxidation "
                        "of methylbenzene with chromyl chloride or $CrO_3$ in the presence of acetic anhydride, formylation "
                        "of arenes, or hydrolysis of benzal chloride. Ketones are prepared by oxidation of secondary alcohols "
                        "and hydration of alkynes. Both can be prepared by ozonolysis of alkenes."
                    ),
                    "content_type": "explanation",
                    "worked_examples": [],
                    "diagrams": [],
                    "tables": []
                },
                {
                    "order": 2,
                    "title": "Reactions of Aldehydes and Ketones",
                    "content_text": (
                        "Aldehydes and ketones undergo nucleophilic addition reactions with HCN, $NaHSO_3$, alcohols, "
                        "ammonia derivatives, and Grignard reagents. Aldehydes and ketones having $\\alpha$-hydrogens "
                        "undergo Aldol condensation in presence of base. Aldehydes with no $\\alpha$-hydrogen undergo "
                        "Cannizzaro reaction with concentrated alkali. They are reduced to alcohols with $NaBH_4$, $LiAlH_4$, "
                        "or catalytic hydrogenation. The carbonyl group can be reduced to a methylene group by Clemmensen "
                        "reduction or Wolff-Kishner reduction. Aldehydes are easily oxidised to carboxylic acids by Tollens' "
                        "reagent and Fehling's reagent, distinguishing them from ketones."
                    ),
                    "content_type": "explanation",
                    "worked_examples": [],
                    "diagrams": [],
                    "tables": []
                },
                {
                    "order": 3,
                    "title": "Carboxylic Acids",
                    "content_text": (
                        "Carboxylic acids are prepared by oxidation of primary alcohols, aldehydes and alkenes, hydrolysis "
                        "of nitriles, and treatment of Grignard reagents with carbon dioxide. Aromatic carboxylic acids are "
                        "prepared by side-chain oxidation of alkylbenzenes. Carboxylic acids are considerably more acidic "
                        "than alcohols and most simple phenols. They are reduced to primary alcohols with $LiAlH_4$ or "
                        "diborane and undergo $\\alpha$-halogenation via the Hell-Volhard-Zelinsky reaction."
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
    # 4. Fix exercise numbering and add exercises
    # =========================================================================
    existing_ex = ch.get("exercises", {}).get("items", [])
    # Current: [1, 2, 3, 8, 17, 18, 19, 20] — renumber sequentially
    for idx, ex in enumerate(existing_ex, 1):
        ex["number"] = idx
    print(f"  ✅ Renumbered {len(existing_ex)} existing exercises (1-{len(existing_ex)})")

    # Add 16 end-of-chapter exercises
    new_exercises = [
        {"number": 9, "problem": "What is meant by the following terms? Give an example of the reaction in each case. (i) Cyanohydrin (ii) Acetal (iii) Semicarbazone (iv) Aldol (v) Hemiacetal (vi) Oxime (vii) Ketal (viii) Imine (ix) 2,4-DNP-derivative (x) Schiff's base", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:nucleophilic_addition", "concept:carbonyl_derivatives"]},
        {"number": 10, "problem": "Name the following compounds according to IUPAC system of nomenclature: (i) $CH_3CH(CH_3)CH_2CH_2CHO$ (ii) $CH_3CH_2COCH(C_2H_5)CH_2CH_2Cl$ (iii) $CH_3CH=CHCHO$ (iv) $CH_3COCH_2COCH_3$ (v) $CH_3CH(CH_3)CH_2C(CH_3)_2COCH_3$ (vi) $(CH_3)_3CCH_2COOH$ (vii) $OHC$-$C_6H_4$-$CHO$-$p$", "solution": None, "difficulty": "easy", "exercise_type": "application", "tests": ["concept:iupac_nomenclature"]},
        {"number": 11, "problem": "Draw the structures of the following compounds: (i) 3-Methylbutanal (ii) p-Nitropropiophenone (iii) p-Methylbenzaldehyde (iv) 4-Methylpent-3-en-2-one (v) 4-Chloropentan-2-one (vi) 3-Bromo-4-phenylpentanoic acid (vii) p,p'-Dihydroxybenzophenone (viii) Hex-2-en-4-ynoic acid", "solution": None, "difficulty": "easy", "exercise_type": "application", "tests": ["concept:structural_formulas"]},
        {"number": 12, "problem": "Write the IUPAC names of the following ketones and aldehydes. Wherever possible, give also common names. (i) $CH_3CO(CH_2)_4CH_3$ (ii) $CH_3CH_2CHBrCH_2CH(CH_3)CHO$ (iii) $CH_3(CH_2)_5CHO$ (iv) $Ph$-$CH=CH$-$CHO$ (v) $PhCOPh$", "solution": None, "difficulty": "easy", "exercise_type": "application", "tests": ["concept:iupac_nomenclature"]},
        {"number": 13, "problem": "Draw structures of the following derivatives: (i) The 2,4-dinitrophenylhydrazone of benzaldehyde (ii) Cyclopropanone oxime (iii) Acetaldehydedimethylacetal (iv) The semicarbazone of cyclobutanone (v) The ethylene ketal of hexan-3-one (vi) The methyl hemiacetal of formaldehyde", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests": ["concept:carbonyl_derivatives"]},
        {"number": 14, "problem": "Predict the products formed when cyclohexanecarbaldehyde reacts with following reagents: (i) $PhMgBr$ and then $H_3O^+$ (ii) Tollens' reagent (iii) Semicarbazide and weak acid (iv) Excess ethanol and acid (v) Zinc amalgam and dilute hydrochloric acid", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests": ["concept:nucleophilic_addition", "concept:clemmensen_reduction"]},
        {"number": 15, "problem": "Which of the following compounds would undergo aldol condensation, which the Cannizzaro reaction and which neither? Write the structures of the expected products. (i) Methanal (ii) 2-Methylpentanal (iii) Benzaldehyde (iv) Benzophenone (v) Cyclohexanone (vi) 1-Phenylpropanone (vii) Phenylacetaldehyde (viii) Butan-1-ol (ix) 2,2-Dimethylbutanal", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:aldol_condensation", "concept:cannizzaro_reaction"]},
        {"number": 16, "problem": "How will you convert ethanol into the following compounds? (i) Butane-1,3-diol (ii) But-2-enal (iii) But-2-enoic acid", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests": ["concept:organic_conversions"]},
        {"number": 17, "problem": "Write structural formulas and names of four possible aldol condensation products from propanal and butanal. In each case, indicate which aldehyde acts as nucleophile and which as electrophile.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:cross_aldol_condensation"]},
        {"number": 18, "problem": "An organic compound with the molecular formula $C_9H_{10}O$ forms 2,4-DNP derivative, reduces Tollens' reagent and undergoes Cannizzaro reaction. On vigorous oxidation, it gives 1,2-benzenedicarboxylic acid. Identify the compound.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:identification_of_compounds"]},
        {"number": 19, "problem": "An organic compound (A) (molecular formula $C_8H_{16}O_2$) was hydrolysed with dilute sulphuric acid to give a carboxylic acid (B) and an alcohol (C). Oxidation of (C) with chromic acid produced (B). (C) on dehydration gives but-1-ene. Write equations for the reactions involved.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:identification_of_compounds"]},
        {"number": 20, "problem": "Arrange the following compounds in increasing order of their property as indicated: (i) Acetaldehyde, Acetone, Di-tert-butyl ketone, Methyl tert-butyl ketone (reactivity towards HCN) (ii) $CH_3CH_2CH(Br)COOH$, $CH_3CH(Br)CH_2COOH$, $(CH_3)_2CHCOOH$, $CH_3CH_2CH_2COOH$ (acid strength) (iii) Benzoic acid, 4-Nitrobenzoic acid, 3,4-Dinitrobenzoic acid, 4-Methoxybenzoic acid (acid strength)", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:reactivity_comparison", "concept:acid_strength"]},
        {"number": 21, "problem": "Give simple chemical tests to distinguish between the following pairs of compounds: (i) Propanal and Propanone (ii) Acetophenone and Benzophenone (iii) Phenol and Benzoic acid (iv) Benzoic acid and Ethyl benzoate (v) Pentan-2-one and Pentan-3-one (vi) Benzaldehyde and Acetophenone (vii) Ethanal and Propanal", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:chemical_tests"]},
        {"number": 22, "problem": "How will you prepare the following compounds from benzene? You may use any inorganic reagent and any organic reagent having not more than one carbon atom. (i) Methyl benzoate (ii) m-Nitrobenzoic acid (iii) p-Nitrobenzoic acid (iv) Phenylacetic acid (v) p-Nitrobenzaldehyde", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:organic_synthesis"]},
        {"number": 23, "problem": "How will you bring about the following conversions in not more than two steps? (i) Propanone to Propene (ii) Benzoic acid to Benzaldehyde (iii) Ethanol to 3-Hydroxybutanal (iv) Benzene to m-Nitroacetophenone (v) Benzaldehyde to Benzophenone (vi) Bromobenzene to 1-Phenylethanol (vii) Benzaldehyde to 3-Phenylpropan-1-ol (viii) Benzaldehyde to $\\alpha$-Hydroxyphenylacetic acid (ix) Benzoic acid to m-Nitrobenzyl alcohol", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:organic_conversions"]},
        {"number": 24, "problem": "Describe the following: (i) Acetylation (ii) Cannizzaro reaction (iii) Cross aldol condensation (iv) Decarboxylation", "solution": None, "difficulty": "easy", "exercise_type": "conceptual", "tests": ["concept:named_reactions"]}
    ]

    existing_ex.extend(new_exercises)
    print(f"  ✅ Added {len(new_exercises)} end-of-chapter exercises (total: {len(existing_ex)})")

    # =========================================================================
    # 5. Clean markers
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
