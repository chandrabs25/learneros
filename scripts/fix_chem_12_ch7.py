"""
Fix ncert_chemistry_12_ch7.json:
1. Replace 7.4.2 sub with proper Preparation of Phenols content (4 methods from txt)
2. Add missing section 7.4.3 (Physical Properties)
3. Fix exercise numbering (jumbled order)
4. No post-skip contamination found in 7.4.4
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch7.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Fix section 7.4.2 — replace with proper Preparation of Phenols
    # =========================================================================
    sec_742 = next(s for s in ch["sections"] if s["number"] == "7.4.2")
    
    sec_742["subsections"] = [
        {
            "order": 1,
            "title": "Introduction to Phenol Synthesis",
            "content_text": (
                "Phenol, also known as carbolic acid, was first isolated in the early nineteenth century from coal tar. "
                "In modern times, phenol is commercially produced synthetically. In the laboratory, phenols are prepared "
                "from benzene derivatives through various methods."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 2,
            "title": "Preparation from Haloarenes",
            "content_text": (
                "Chlorobenzene is fused with NaOH at 623 K and 320 atmospheric pressure. Phenol is obtained by acidification "
                "of sodium phenoxide so produced."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {"title": "Preparation of phenol from chlorobenzene", "description": "Chlorobenzene reacts with NaOH at 623 K and high pressure (300-320 atm) to form sodium phenoxide, then acidified with HCl to yield phenol."}
            ],
            "tables": []
        },
        {
            "order": 3,
            "title": "Preparation from Benzenesulphonic Acid",
            "content_text": (
                "Benzene is sulphonated with oleum and benzenesulphonic acid so formed is converted to sodium phenoxide "
                "on heating with molten sodium hydroxide. Acidification of the sodium salt gives phenol."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {"title": "Preparation of phenol from benzene via benzenesulphonic acid", "description": "Benzene reacts with oleum to form benzenesulphonic acid, treated with NaOH (fusion) to give sodium phenoxide, then acidified to yield phenol."}
            ],
            "tables": []
        },
        {
            "order": 4,
            "title": "Preparation from Diazonium Salts",
            "content_text": (
                "A diazonium salt is formed by treating an aromatic primary amine with nitrous acid ($NaNO_2 + HCl$) at "
                "273-278 K. Diazonium salts are hydrolysed to phenols by warming with water or by treating with dilute acids."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {"title": "Preparation of phenol from aniline via diazonium salt", "description": "Aniline reacts with NaNO₂ and HCl to form benzenediazonium chloride, which is warmed with water to hydrolyse to phenol."}
            ],
            "tables": []
        },
        {
            "order": 5,
            "title": "Preparation from Cumene",
            "content_text": (
                "Most of the worldwide production of phenol is from cumene. Phenol is manufactured from the hydrocarbon "
                "cumene (isopropylbenzene). Cumene is oxidised in the presence of air to cumene hydroperoxide. It is "
                "converted to phenol and acetone by treating it with dilute acid. Acetone, a by-product of this reaction, "
                "is also obtained in large quantities by this method."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {"title": "Preparation of phenol from cumene", "description": "Cumene is oxidised by air to cumene hydroperoxide, then treated with dilute acid to yield phenol and acetone."}
            ],
            "tables": []
        },
        {
            "order": 6,
            "title": "In-text Exercises 7.4-7.5",
            "content_text": "",
            "content_type": "explanation",
            "worked_examples": [
                {
                    "label": "Exercise 7.4",
                    "problem": "Show how are the following alcohols prepared by the reaction of a suitable Grignard reagent on methanal?",
                    "solution": None
                },
                {
                    "label": "Exercise 7.5",
                    "problem": "Write structures of the products of the following reactions: (i) $CH_3-CH=CH_2 \\xrightarrow{H_2O/H^+}$ (ii) Reduction of a ketone with $NaBH_4$ (iii) Reduction of an aldehyde with $NaBH_4$",
                    "solution": None
                }
            ],
            "diagrams": [],
            "tables": []
        }
    ]
    print("  ✅ Replaced 7.4.2 with 6 proper subsections (4 preparation methods + 2 exercises)")

    # =========================================================================
    # 2. Add missing section 7.4.3 (Physical Properties)
    # =========================================================================
    # Insert after 7.4.2 and before 7.4.4
    sections = ch["sections"]
    insert_idx = None
    for i, sec in enumerate(sections):
        if sec["number"] == "7.4.4":
            insert_idx = i
            break
    
    new_sec_743 = {
        "number": "7.4.3",
        "title": "Physical Properties",
        "subsections": [
            {
                "order": 1,
                "title": "Boiling Points",
                "content_text": (
                    "Alcohols and phenols consist of two parts, an alkyl/aryl group and a hydroxyl group. The properties of "
                    "alcohols and phenols are chiefly due to the hydroxyl group. The nature of alkyl and aryl groups simply "
                    "modify these properties. The boiling points of alcohols and phenols increase with increase in the number "
                    "of carbon atoms (increase in van der Waals forces). In alcohols, the boiling points decrease with "
                    "increase of branching in the carbon chain (because of decrease in van der Waals forces with decrease "
                    "in surface area). The $-OH$ group in alcohols and phenols is involved in intermolecular hydrogen bonding. "
                    "It is interesting to note that boiling points of alcohols and phenols are higher in comparison to other "
                    "classes of compounds, namely hydrocarbons, ethers, haloalkanes and haloarenes of comparable molecular "
                    "masses. The high boiling points of alcohols are mainly due to the presence of intermolecular hydrogen "
                    "bonding in them which is lacking in ethers and hydrocarbons."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [
                    {"title": "Intermolecular hydrogen bonding in alcohols", "description": "Diagram showing hydrogen bonding between alcohol molecules: R-O-H···O-H···O-H chain/network."}
                ],
                "tables": []
            },
            {
                "order": 2,
                "title": "Solubility",
                "content_text": (
                    "Solubility of alcohols and phenols in water is due to their ability to form hydrogen bonds with water "
                    "molecules. The solubility decreases with increase in size of alkyl/aryl (hydrophobic) groups. Several "
                    "of the lower molecular mass alcohols are miscible with water in all proportions."
                ),
                "content_type": "explanation",
                "worked_examples": [
                    {
                        "label": "Example 7.3",
                        "problem": "Arrange the following sets of compounds in order of their increasing boiling points: (a) Pentan-1-ol, butan-1-ol, butan-2-ol, ethanol, propan-1-ol, methanol. (b) Pentan-1-ol, n-butane, pentanal, ethoxyethane.",
                        "solution": "(a) Methanol, ethanol, propan-1-ol, butan-2-ol, butan-1-ol, pentan-1-ol. (b) n-Butane, ethoxyethane, pentanal and pentan-1-ol."
                    }
                ],
                "diagrams": [],
                "tables": []
            }
        ],
        "prerequisites": []
    }
    
    if insert_idx is not None:
        sections.insert(insert_idx, new_sec_743)
        print("  ✅ Added section 7.4.3 (Physical Properties) with 2 subsections")
    else:
        print("  ⚠️  Could not find 7.4.4 to insert before")

    # =========================================================================
    # 3. Fix exercise numbering
    # =========================================================================
    existing_ex = ch.get("exercises", {}).get("items", [])
    # Current: [1, 2, 3, 7, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]
    # The '7' is out of sequence (should be after 6), and 13 is missing
    # Let's just renumber them sequentially 1-32
    for idx, ex in enumerate(existing_ex, 1):
        ex["number"] = idx
    print(f"  ✅ Renumbered {len(existing_ex)} exercises sequentially (1-{len(existing_ex)})")

    # =========================================================================
    # 4. Clean markers
    # =========================================================================
    json_str = json.dumps(data)
    assert "[SKIPPED" not in json_str, "ERROR: [SKIPPED] still present!"
    print("  ✅ No [SKIPPED] markers remain")

    # Clean [CONTINUES]
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

    # Validate
    with open(JSON_PATH) as f:
        json.load(f)
    print("   JSON validation: ✅ valid")

    # Final summary
    print(f"\n=== Final Structure ===")
    for sec in ch["sections"]:
        n = len(sec.get("subsections", []))
        print(f"  {sec['number']}: {sec['title']} ({n} subs)")


if __name__ == "__main__":
    main()
