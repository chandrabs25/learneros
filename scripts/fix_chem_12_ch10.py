"""
Fix ncert_chemistry_12_ch10.json:
1. Fix 10.4: replace SKIPPED sub with vitamins classification + Table 10.3
2. Add missing 10.5 intro content (nucleic acids intro, Watson, chemical composition, structure)
3. Fix exercise numbering (has 106,107,108 in middle)
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch10.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Fix section 10.4 — replace SKIPPED sub with vitamins content
    # =========================================================================
    sec_104 = next(s for s in ch["sections"] if s["number"] == "10.4")
    
    # Remove SKIPPED sub
    sec_104["subsections"] = [
        s for s in sec_104["subsections"]
        if "[SKIPPED" not in (s.get("title") or "")
    ]
    
    # Clean [CONTINUES] from last sub
    if sec_104["subsections"]:
        last = sec_104["subsections"][-1]
        ct = last.get("content_text", "")
        if "[CONTINUES]" in ct:
            last["content_text"] = ct.replace("[CONTINUES]", "").rstrip()

    # Add vitamin classification and table
    sec_104["subsections"].extend([
        {
            "order": 2,
            "title": "Origin of the Term 'Vitamin'",
            "content_text": (
                "The term 'Vitamin' was coined from the word vital + amine since the earlier identified compounds "
                "had amino groups. Later work showed that most of them did not contain amino groups, so the letter "
                "'e' was dropped and the term vitamin is used these days. Vitamins are designated by alphabets A, B, C, D, etc. "
                "Some of them are further named as sub-groups e.g. $B_1$, $B_2$, $B_6$, $B_{12}$, etc. Excess of vitamins "
                "is also harmful and vitamin pills should not be taken without the advice of a doctor."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 3,
            "title": "Classification of Vitamins",
            "content_text": (
                "Vitamins are classified into two groups depending upon their solubility in water or fat.\n\n"
                "(i) Fat soluble vitamins: Vitamins which are soluble in fat and oils but insoluble in water are kept "
                "in this group. These are vitamins A, D, E and K. They are stored in liver and adipose (fat storing) tissues.\n\n"
                "(ii) Water soluble vitamins: B group vitamins and vitamin C are soluble in water so they are grouped "
                "together. Water soluble vitamins must be supplied regularly in diet because they are readily excreted "
                "in urine and cannot be stored (except vitamin $B_{12}$) in our body."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": [
                {
                    "title": "Some Important Vitamins, their Sources and their Deficiency Diseases",
                    "headers": ["Name of Vitamin", "Source", "Deficiency Diseases"],
                    "rows": [
                        ["Vitamin A", "Fish liver oil, carrots, butter, milk", "Xerophthalmia (hardening of cornea), Night blindness"],
                        ["Vitamin B₁ (Thiamine)", "Yeast, milk, green vegetables, cereals", "Beri beri (loss of appetite, retarded growth)"],
                        ["Vitamin B₂ (Riboflavin)", "Milk, eggwhite, liver, kidney", "Cheilosis (fissuring at corners of mouth and lips), digestive disorders"],
                        ["Vitamin B₆ (Pyridoxine)", "Yeast, milk, egg yolk, cereals", "Convulsions"],
                        ["Vitamin B₁₂", "Meat, fish, egg, curd", "Pernicious anaemia (RBC deficient in haemoglobin)"],
                        ["Vitamin C (Ascorbic acid)", "Citrus fruits, amla, green leafy vegetables", "Scurvy (bleeding gums)"],
                        ["Vitamin D", "Exposure to sunlight, fish and egg yolk", "Rickets (bone deformities in children), Osteomalacia (soft bones in adults)"],
                        ["Vitamin E", "Vegetable oils like wheat germ oil, sunflower oil", "Increased fragility of RBCs and muscular weakness"],
                        ["Vitamin K", "Green leafy vegetables", "Increased blood clotting time"]
                    ]
                }
            ]
        }
    ])
    
    # Renumber
    for idx, sub in enumerate(sec_104["subsections"], 1):
        sub["order"] = idx
    print(f"  ✅ Fixed 10.4: added vitamins classification + Table 10.3 ({len(sec_104['subsections'])} subs)")

    # =========================================================================
    # 2. Add missing 10.5 intro content
    # =========================================================================
    sec_105 = next(s for s in ch["sections"] if s["number"] == "10.5")
    
    # The existing subs start with "Structure of Nucleic Acids" (phosphodiester linkage)
    # Missing: intro, Watson bio, chemical composition, nucleoside/nucleotide structure
    # Insert at the beginning
    new_intro_subs = [
        {
            "order": 0,
            "title": "Introduction to Nucleic Acids",
            "content_text": (
                "Every generation of each and every species resembles its ancestors in many ways. The nucleus of a living cell "
                "is responsible for this transmission of inherent characters, also called heredity. The particles in the nucleus "
                "of the cell, responsible for heredity, are called chromosomes which are made up of proteins and another type of "
                "biomolecules called nucleic acids. These are mainly of two types, the deoxyribonucleic acid (DNA) and "
                "ribonucleic acid (RNA). Since nucleic acids are long chain polymers of nucleotides, they are also called "
                "polynucleotides."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 0,
            "title": "Chemical Composition of Nucleic Acids",
            "content_text": (
                "Complete hydrolysis of DNA (or RNA) yields a pentose sugar, phosphoric acid and nitrogen containing "
                "heterocyclic compounds (called bases). In DNA molecules, the sugar moiety is $\\beta$-D-2-deoxyribose "
                "whereas in RNA molecule, it is $\\beta$-D-ribose. DNA contains four bases viz. adenine (A), guanine (G), "
                "cytosine (C) and thymine (T). RNA also contains four bases, the first three bases are same as in DNA but "
                "the fourth one is uracil (U)."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {"title": "Pentose sugars in nucleic acids", "description": "Chemical structures of β-D-ribose (in RNA) and β-D-2-deoxyribose (in DNA), both as furanose rings."}
            ],
            "tables": []
        },
        {
            "order": 0,
            "title": "Nucleosides and Nucleotides",
            "content_text": (
                "A unit formed by the attachment of a base to 1' position of sugar is known as a nucleoside. In nucleosides, "
                "the sugar carbons are numbered as 1', 2', 3', etc. in order to distinguish these from the bases. When a "
                "nucleoside is linked to phosphoric acid at 5'-position of sugar moiety, we get a nucleotide. Nucleotides "
                "are joined together by phosphodiester linkage between 5' and 3' carbon atoms of the pentose sugar."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {"title": "Nucleoside and nucleotide structure", "description": "Diagram (a) shows a nucleoside: ribose sugar connected to adenine. Diagram (b) shows a nucleotide: nucleoside with phosphate group at 5' carbon."},
                {"title": "Dinucleotide formation", "description": "Two nucleotides linked by a phosphodiester bond between 3' of first and 5' of second sugar."}
            ],
            "tables": []
        }
    ]
    
    # Insert at beginning
    for i, new_sub in enumerate(reversed(new_intro_subs)):
        sec_105["subsections"].insert(0, new_sub)
    
    # Renumber
    for idx, sub in enumerate(sec_105["subsections"], 1):
        sub["order"] = idx
    print(f"  ✅ Added 3 intro subsections to 10.5 ({len(sec_105['subsections'])} subs total)")

    # =========================================================================
    # 3. Fix exercise numbering
    # =========================================================================
    existing_ex = ch.get("exercises", {}).get("items", [])
    # Current: [1, 2, 3, 4, 5, 106, 107, 108, 6, 7, ...] — renumber sequentially
    for idx, ex in enumerate(existing_ex, 1):
        ex["number"] = idx
    print(f"  ✅ Renumbered {len(existing_ex)} exercises (1-{len(existing_ex)})")

    # =========================================================================
    # 4. Clean markers
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
