"""
Fix ncert_chemistry_11_ch3.json:
1. Replace corrupted subsection 6 in section 3.7 (has [SKIPPED] marker)
   with 7 proper subsections from the txt file content
2. Renumber all subsequent subsections
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_11_ch3.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    sections = data["chapter"]["sections"]
    sec_37 = next(s for s in sections if s["number"] == "3.7")
    subs = sec_37["subsections"]

    # Find the corrupted subsection (order 6, contains [SKIPPED])
    corrupt_idx = next(i for i, s in enumerate(subs) if s["order"] == 6)
    corrupt_sub = subs[corrupt_idx]
    assert "[SKIPPED" in corrupt_sub["content_text"], "Expected [SKIPPED] marker not found!"

    # Keep the existing diagrams from the corrupted subsection (Fig 3.5, 3.6a, 3.6b)
    existing_diagrams = corrupt_sub.get("diagrams", [])

    # Build the 7 replacement subsections
    new_subs = [
        {
            "order": 6,
            "title": "Ionization Enthalpy: Trends and Shielding",
            "content_text": (
                "The effective nuclear charge experienced by a valence electron in an atom "
                "will be less than the actual charge on the nucleus because of 'shielding' "
                "or 'screening' of the valence electron from the nucleus by the intervening "
                "core electrons. For example, the 2s electron in lithium is shielded from "
                "the nucleus by the inner core of 1s electrons. As a result, the valence "
                "electron experiences a net positive charge which is less than the actual "
                "charge of +3. In general, shielding is effective when the orbitals in the "
                "inner shells are completely filled. This situation occurs in the case of "
                "alkali metals which have single outermost $ns$-electron preceded by a noble "
                "gas electronic configuration. "
                "When we move from lithium to fluorine across the second period, successive "
                "electrons are added to orbitals in the same principal quantum level and the "
                "shielding of the nuclear charge by the inner core of electrons does not "
                "increase very much to compensate for the increased attraction of the electron "
                "to the nucleus. Thus, across a period, increasing nuclear charge outweighs "
                "the shielding. Consequently, the outermost electrons are held more and more "
                "tightly and the ionization enthalpy increases across a period. As we go down "
                "a group, the outermost electron being increasingly farther from the nucleus, "
                "there is an increased shielding of the nuclear charge by the electrons in the "
                "inner levels. In this case, increase in shielding outweighs the increasing "
                "nuclear charge and the removal of the outermost electron requires less energy "
                "down a group."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": existing_diagrams,  # Keep Fig 3.5, 3.6a, 3.6b here
            "tables": []
        },
        {
            "order": 7,
            "title": "Ionization Enthalpy: Anomalies (B vs Be, O vs N)",
            "content_text": (
                "From Fig. 3.6(a), the first ionization enthalpy of boron ($Z = 5$) is "
                "slightly less than that of beryllium ($Z = 4$) even though the former has "
                "a greater nuclear charge. When we consider the same principal quantum level, "
                "an $s$-electron is attracted to the nucleus more than a $p$-electron. In "
                "beryllium, the electron removed during the ionization is an $s$-electron "
                "whereas the electron removed during ionization of boron is a $p$-electron. "
                "The penetration of a $2s$-electron to the nucleus is more than that of a "
                "$2p$-electron; hence the $2p$ electron of boron is more shielded from the "
                "nucleus by the inner core of electrons than the $2s$ electrons of beryllium. "
                "Therefore, it is easier to remove the $2p$-electron from boron compared to "
                "the removal of a $2s$-electron from beryllium. Thus, boron has a smaller "
                "first ionization enthalpy than beryllium. "
                "Another anomaly is the smaller first ionization enthalpy of oxygen compared "
                "to nitrogen. This arises because in the nitrogen atom, three $2p$-electrons "
                "reside in different atomic orbitals (Hund's rule) whereas in the oxygen atom, "
                "two of the four $2p$-electrons must occupy the same $2p$-orbital resulting in "
                "an increased electron-electron repulsion. Consequently, it is easier to remove "
                "the fourth $2p$-electron from oxygen than it is to remove one of the three "
                "$2p$-electrons from nitrogen."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 8,
            "title": "Worked Example: Predicting Ionization Enthalpy of Al",
            "content_text": (
                "Prediction of the first ionization enthalpy of aluminium based on "
                "trends observed across the third period."
            ),
            "content_type": "application",
            "worked_examples": [
                {
                    "label": "Problem 3.6",
                    "problem": (
                        "The first ionization enthalpy ($\\Delta_i H$) values of the third "
                        "period elements, Na, Mg and Si are respectively 496, 737 and 786 "
                        "kJ mol$^{-1}$. Predict whether the first $\\Delta_i H$ value for Al "
                        "will be more close to 575 or 760 kJ mol$^{-1}$? Justify your answer."
                    ),
                    "solution": (
                        "It will be more close to 575 kJ mol$^{-1}$. The value for Al should "
                        "be lower than that of Mg because of effective shielding of $3p$ "
                        "electrons from the nucleus by $3s$-electrons."
                    )
                }
            ],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 9,
            "title": "Electron Gain Enthalpy",
            "content_text": (
                "When an electron is added to a neutral gaseous atom ($X$) to convert it "
                "into a negative ion, the enthalpy change accompanying the process is "
                "defined as the Electron Gain Enthalpy ($\\Delta_{eg}H$). Electron gain "
                "enthalpy provides a measure of the ease with which an atom adds an electron "
                "to form an anion as represented by equation 3.3: "
                "$X(g) + e^- \\rightarrow X^-(g)$. "
                "Depending on the element, the process of adding an electron to the atom can "
                "be either endothermic or exothermic. For many elements energy is released "
                "when an electron is added to the atom and the electron gain enthalpy is "
                "negative. For example, group 17 elements (the halogens) have very high "
                "negative electron gain enthalpies because they can attain stable noble gas "
                "electronic configurations by picking up an electron. "
                "On the other hand, noble gases have large positive electron gain enthalpies "
                "because the electron has to enter the next higher principal quantum level "
                "leading to a very unstable electronic configuration. It may be noted that "
                "electron gain enthalpies have large negative values toward the upper right "
                "of the periodic table preceding the noble gases."
            ),
            "content_type": "definition",
            "worked_examples": [],
            "diagrams": [],
            "tables": [
                {
                    "label": "Table 3.7",
                    "caption": "Electron Gain Enthalpies (kJ mol$^{-1}$) of Some Main Group Elements",
                    "headers": [
                        "Group 1", "$\\Delta_{eg}H$",
                        "Group 16", "$\\Delta_{eg}H$",
                        "Group 17", "$\\Delta_{eg}H$",
                        "Group 0", "$\\Delta_{eg}H$"
                    ],
                    "rows": [
                        ["H", "–73", "", "", "", "", "He", "+48"],
                        ["Li", "–60", "O", "–141", "F", "–328", "Ne", "+116"],
                        ["Na", "–53", "S", "–200", "Cl", "–349", "Ar", "+96"],
                        ["K", "–48", "Se", "–195", "Br", "–325", "Kr", "+96"],
                        ["Rb", "–47", "Te", "–190", "I", "–295", "Xe", "+77"],
                        ["Cs", "–46", "Po", "–174", "At", "–270", "Rn", "+68"]
                    ]
                }
            ]
        },
        {
            "order": 10,
            "title": "Electron Gain Enthalpy: Trends",
            "content_text": (
                "The variation in electron gain enthalpies of elements is less systematic "
                "than for ionization enthalpies. As a general rule, electron gain enthalpy "
                "becomes more negative with increase in the atomic number across a period. "
                "The effective nuclear charge increases from left to right across a period "
                "and consequently it will be easier to add an electron to a smaller atom "
                "since the added electron on an average would be closer to the positively "
                "charged nucleus. We should also expect electron gain enthalpy to become "
                "less negative as we go down a group because the size of the atom increases "
                "and the added electron would be farther from the nucleus. This is generally "
                "the case (Table 3.7). However, electron gain enthalpy of O or F is less "
                "negative than that of the succeeding element. This is because when an "
                "electron is added to O or F, the added electron goes to the smaller $n = 2$ "
                "quantum level and suffers significant repulsion from the other electrons "
                "present in this level. For the $n = 3$ quantum level (S or Cl), the added "
                "electron occupies a larger region of space and the electron-electron "
                "repulsion is much less."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 11,
            "title": "Worked Example: Electron Gain Enthalpy Comparison",
            "content_text": (
                "Comparison of electron gain enthalpies for elements in the same period "
                "and group."
            ),
            "content_type": "application",
            "worked_examples": [
                {
                    "label": "Problem 3.7",
                    "problem": (
                        "Which of the following will have the most negative electron gain "
                        "enthalpy and which the least negative? P, S, Cl, F. Explain your answer."
                    ),
                    "solution": (
                        "Electron gain enthalpy generally becomes more negative across a period "
                        "as we move from left to right. Within a group, electron gain enthalpy "
                        "becomes less negative down a group. However, adding an electron to the "
                        "$2p$-orbital leads to greater repulsion than adding an electron to the "
                        "larger $3p$-orbital. Hence the element with most negative electron gain "
                        "enthalpy is chlorine; the one with the least negative electron gain "
                        "enthalpy is phosphorus."
                    )
                }
            ],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 12,
            "title": "Electronegativity",
            "content_text": (
                "A qualitative measure of the ability of an atom in a chemical compound to "
                "attract shared electrons to itself is called electronegativity. Unlike "
                "ionization enthalpy and electron gain enthalpy, it is not a measurable "
                "quantity. However, a number of numerical scales of electronegativity of "
                "elements viz., Pauling scale, Mulliken-Jaffe scale, Allred-Rochow scale "
                "have been developed. The one which is the most widely used is the Pauling "
                "scale. Linus Pauling, an American scientist, in 1932 assigned arbitrarily "
                "a value of 4.0 to fluorine, the element considered to have the greatest "
                "ability to attract electrons. Approximate values for the electronegativity "
                "of a few elements are given in Table 3.8(a). "
                "The electronegativity of any given element is not constant; it varies "
                "depending on the element to which it is bound. Though it is not a measurable "
                "quantity, it does provide a means of predicting the nature of force that "
                "holds a pair of atoms together. "
                "Electronegativity generally increases across a period from left to right "
                "(say from lithium to fluorine) and decreases down a group (say from fluorine "
                "to astatine) in the periodic table. The attraction between the outer (or "
                "valence) electrons and the nucleus increases as the atomic radius decreases "
                "in a period. The electronegativity also increases. On the same account "
                "electronegativity values decrease with the increase in atomic radii down "
                "a group. The trend is similar to that of ionization enthalpy. "
                "Electronegativity is directly related to the non-metallic properties of "
                "elements. Conversely, it is inversely related to metallic properties. "
                "Across a period, the increase in electronegativity is accompanied by an "
                "increase in non-metallic properties (or a decrease in metallic properties). "
                "Down a group, the decrease in electronegativity is accompanied by a decrease "
                "in non-metallic properties (or an increase in metallic properties). These "
                "trends are fundamental to understanding the chemical behavior of elements."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [
                {
                    "label": "Fig. 3.7",
                    "description": (
                        "The periodic trends of elements in the periodic table showing "
                        "electronegativity values on the Pauling scale."
                    ),
                    "image_url": None
                }
            ],
            "tables": [
                {
                    "label": "Table 3.8(a)",
                    "caption": "Electronegativity Values (on Pauling scale) Across the Periods",
                    "headers": [
                        "Period", "Li/Na", "Be/Mg", "B/Al", "C/Si", "N/P", "O/S", "F/Cl"
                    ],
                    "rows": [
                        ["Period II", "1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0"],
                        ["Period III", "0.9", "1.2", "1.5", "1.8", "2.1", "2.5", "3.0"]
                    ]
                },
                {
                    "label": "Table 3.8(b)",
                    "caption": "Electronegativity Values (on Pauling scale) Down a Family",
                    "headers": [
                        "Atom (Group 1)", "Electronegativity Value",
                        "Atom (Group 17)", "Electronegativity Value"
                    ],
                    "rows": [
                        ["Li", "1.0", "F", "4.0"],
                        ["Na", "0.9", "Cl", "3.0"],
                        ["K", "0.8", "Br", "2.8"],
                        ["Rb", "0.8", "I", "2.5"],
                        ["Cs", "0.7", "At", "2.2"]
                    ]
                }
            ]
        }
    ]

    # Replace corrupted subsection with the new ones
    subs_before = subs[:corrupt_idx]          # orders 1-5
    subs_after = subs[corrupt_idx + 1:]       # orders 7+ (to be renumbered)

    # Renumber the remaining subsections
    next_order = 13  # after our 7 new subs (6-12)
    for sub in subs_after:
        sub["order"] = next_order
        next_order += 1

    # Reassemble
    sec_37["subsections"] = subs_before + new_subs + subs_after

    print(f"  ✅ Replaced corrupted subsection 6 with {len(new_subs)} new subsections")
    print(f"  ✅ Renumbered {len(subs_after)} subsequent subsections (13–{12 + len(subs_after)})")
    print(f"  Total subsections in 3.7: {len(sec_37['subsections'])}")

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

    # Print final subsection list
    print("\n=== Section 3.7 subsections ===")
    for sub in sec_37["subsections"]:
        print(f"  order {sub['order']:2d}: {sub['title']}")


if __name__ == "__main__":
    main()
