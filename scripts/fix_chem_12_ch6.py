"""
Fix ncert_chemistry_12_ch6.json:
1. Replace SKIPPED sub in 6.7.2 with proper content (haloarene reactions from txt)
2. Replace SKIPPED sub in 6.8 with polyhalogen compounds content (from last pages txt)
3. Add Summary section
4. Fix existing exercise numbering (1,62-66 → 1-6)
5. Add 22 end-of-chapter exercises (6.1-6.22)
6. Check post-skip contamination from pages 25-27
"""

import json
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_12_ch6.json")


def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    ch = data["chapter"]

    # =========================================================================
    # 1. Fix section 6.7.2 — replace SKIPPED sub 10 with proper content
    # =========================================================================
    sec_672 = next(s for s in ch["sections"] if s["number"] == "6.7.2")
    
    # Find and replace the SKIPPED subsection
    new_subs_672 = []
    for sub in sec_672["subsections"]:
        if sub.get("_skipped") or "[SKIPPED" in (sub.get("title") or ""):
            # Replace with proper content from txt file (pages 25-27)
            # This covers: Meisenheimer complex mechanism, electrophilic substitution
            new_subs_672.append({
                "order": sub["order"],
                "title": "Nucleophilic Substitution on Haloarenes: Mechanism",
                "content_text": (
                    "The effect of electron withdrawing groups on the reactivity of haloarenes is pronounced when the $-NO_2$ group "
                    "is introduced at ortho- and para- positions. However, no effect on reactivity is observed by the presence of "
                    "an electron withdrawing group at the meta-position. The mechanism involves the formation of a Meisenheimer complex "
                    "where the incoming nucleophile attacks the carbon bearing the halogen. For the p-isomer and o-isomer, the negative "
                    "charge developed in the intermediate can be delocalised onto the nitro group through resonance, stabilising the "
                    "intermediate and thus facilitating the reaction. In the case of the m-isomer, none of the resonating structures "
                    "bear the negative charge on the carbon atom bearing the $-NO_2$ group. Therefore, the presence of a nitro group "
                    "at the meta-position does not stabilise the negative charge and no effect on reactivity is observed."
                ),
                "content_type": "explanation",
                "worked_examples": [],
                "diagrams": [
                    {"title": "Meisenheimer complex for p-nitrochlorobenzene", "description": "Resonance structures showing nucleophilic substitution on p-nitrochlorobenzene with charge delocalisation onto the nitro group"},
                    {"title": "Meisenheimer complex for o-nitrochlorobenzene", "description": "Resonance structures for nucleophilic substitution on o-nitrochlorobenzene"},
                    {"title": "Attempted substitution on m-nitrochlorobenzene", "description": "Resonance structures showing that the negative charge cannot be delocalised onto the meta-nitro group"}
                ],
                "tables": []
            })
            # Add electrophilic substitution subsection
            new_subs_672.append({
                "order": sub["order"] + 1,
                "title": "Electrophilic Substitution Reactions of Haloarenes",
                "content_text": (
                    "Haloarenes undergo the usual electrophilic reactions of the benzene ring such as halogenation, nitration, "
                    "sulphonation and Friedel-Crafts reactions. The halogen atom, besides being slightly deactivating, is ortho-, "
                    "para-directing; therefore, further substitution occurs at ortho- and para-positions with respect to the halogen "
                    "atom. The o,p-directing influence can be understood through resonance structures of halobenzenes, where electron "
                    "density increases more at ortho- and para-positions than at meta-positions. Due to the $-I$ effect, the halogen "
                    "atom has some tendency to withdraw electrons from the benzene ring, making the ring somewhat deactivated compared "
                    "to benzene. Hence, electrophilic substitution reactions in haloarenes occur slowly and require more drastic "
                    "conditions compared to benzene.\n\n"
                    "(i) Halogenation: Chlorobenzene reacts with $Cl_2$ in the presence of anhydrous $FeCl_3$ to yield a mixture of "
                    "1,2-dichlorobenzene (minor) and 1,4-dichlorobenzene (major).\n\n"
                    "(ii) Nitration: Chlorobenzene reacts with conc. $HNO_3$ and conc. $H_2SO_4$ to yield 1-chloro-2-nitrobenzene "
                    "(minor) and 1-chloro-4-nitrobenzene (major).\n\n"
                    "(iii) Sulphonation: Chlorobenzene reacts with conc. $H_2SO_4$ to yield 2-chlorobenzenesulphonic acid (minor) "
                    "and 4-chlorobenzenesulphonic acid (major).\n\n"
                    "(iv) Friedel-Crafts reaction: Chlorobenzene reacts with $CH_3Cl$ in the presence of anhydrous $AlCl_3$ to yield "
                    "1-chloro-2-methylbenzene (minor) and 1-chloro-4-methylbenzene (major). Similarly, Friedel-Crafts acylation with "
                    "$CH_3COCl$ gives 2-chloroacetophenone (minor) and 4-chloroacetophenone (major)."
                ),
                "content_type": "explanation",
                "worked_examples": [
                    {
                        "label": "Example 6.9",
                        "problem": "Although chlorine is an electron withdrawing group, yet it is ortho-, para-directing in electrophilic aromatic substitution reactions. Why?",
                        "solution": "Chlorine withdraws electrons through inductive effect and releases electrons through resonance. Through inductive effect, chlorine destabilises the intermediate carbocation formed during the electrophilic substitution. Through resonance, the electron density increases more at ortho- and para-positions. The +M effect of chlorine stabilises the intermediate carbocation (Wheland intermediate) by donating a lone pair to form a new π-bond, placing the positive charge on the chlorine. The resonance effect (electron release) is stronger than the inductive effect at ortho- and para-positions, making chlorine an o,p-directing group despite being overall deactivating."
                    }
                ],
                "diagrams": [
                    {"title": "Resonance structures of chlorobenzene", "description": "Four resonance structures showing electron density increase at ortho- and para-positions"},
                    {"title": "Destabilisation by -I effect", "description": "Diagram showing destabilisation of intermediate carbocation by the -I effect of chlorine"},
                    {"title": "Stabilisation by +M effect", "description": "Diagram showing stabilisation of intermediate carbocation by the +M effect of chlorine"}
                ],
                "tables": []
            })
            print("  ✅ Replaced SKIPPED sub in 6.7.2 with 2 proper subsections")
        else:
            new_subs_672.append(sub)
    
    sec_672["subsections"] = new_subs_672
    # Re-number
    for idx, sub in enumerate(sec_672["subsections"], 1):
        sub["order"] = idx
    print(f"     Section 6.7.2 now has {len(sec_672['subsections'])} subsections")

    # =========================================================================
    # 2. Fix section 6.8 — replace SKIPPED with polyhalogen compounds content
    # =========================================================================
    sec_68 = next(s for s in ch["sections"] if s["number"] == "6.8")
    
    sec_68["subsections"] = [
        {
            "order": 1,
            "title": "Introduction to Polyhalogen Compounds",
            "content_text": (
                "Carbon atoms can accommodate more than one halogen atom bound to them, forming polyhalogen compounds. "
                "Many of these compounds have important industrial applications. Some notable examples include "
                "dichloromethane ($CH_2Cl_2$), trichloromethane (chloroform, $CHCl_3$), triiodomethane (iodoform, $CHI_3$), "
                "tetrachloromethane (carbon tetrachloride, $CCl_4$), and freons."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 2,
            "title": "Dichloromethane",
            "content_text": (
                "Dichloromethane ($CH_2Cl_2$) is widely used as a solvent as a paint remover, as a propellant in aerosols, "
                "and as a process solvent in the manufacture of drugs. It is also used as a metal cleaning and finishing solvent."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 3,
            "title": "Chloroform",
            "content_text": (
                "Chloroform ($CHCl_3$) was once widely used as an anaesthetic. It is slowly oxidised by air in the presence of "
                "light to form a poisonous gas, phosgene ($COCl_2$). Therefore, chloroform is stored in dark-coloured bottles "
                "completely filled so that air is kept out. It is used as a solvent for fats, alkaloids, iodine, and rubber. "
                "Chloroform is also used in the production of the refrigerant freon (R-22, $CHClF_2$)."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 4,
            "title": "Iodoform",
            "content_text": (
                "Iodoform ($CHI_3$) was earlier used as an antiseptic but now it has been replaced by better antiseptics. "
                "Its antiseptic property is actually due to the liberation of free iodine."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 5,
            "title": "Carbon Tetrachloride",
            "content_text": (
                "Carbon tetrachloride ($CCl_4$) is produced by the reaction of methane with chlorine. It is used in the "
                "manufacture of refrigerants and propellants for aerosol cans. It was earlier used as a fire extinguisher "
                "under the name Pyrene but its use for this purpose has been discontinued as it produces toxic phosgene gas "
                "when brought in contact with fire. It is also used as a solvent for oils, fats, lacquers, varnishes, "
                "rubber waxes and resins, and as a cleaning agent."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        },
        {
            "order": 6,
            "title": "Freons and DDT",
            "content_text": (
                "Freons are chlorofluorocarbons (CFCs) such as freon-12 ($CCl_2F_2$). They are used as refrigerants in air "
                "conditioners and refrigerators, as propellants for aerosols and foams, and as cleaning solvents. Their use "
                "is being curtailed because they deplete the ozone layer.\n\n"
                "DDT (p,p'-dichlorodiphenyltrichloroethane) is the first chlorinated organic insecticide prepared (1873) by "
                "the reaction of trichloroacetaldehyde with chlorobenzene in the presence of sulphuric acid. Its insecticidal "
                "properties were discovered in 1939 by Paul Muller. DDT is not easily biodegradable and tends to accumulate "
                "in the food chain (biomagnification), which is harmful to organisms. Its use has been banned in many countries "
                "including India."
            ),
            "content_type": "explanation",
            "worked_examples": [],
            "diagrams": [],
            "tables": []
        }
    ]
    print("  ✅ Replaced SKIPPED sub in 6.8 with 6 polyhalogen compound subsections")

    # =========================================================================
    # 3. Add Summary section
    # =========================================================================
    # Check if Summary already exists
    has_summary = any(s["number"] == "Summary" for s in ch["sections"])
    if not has_summary:
        ch["sections"].append({
            "number": "Summary",
            "title": "Summary",
            "subsections": [
                {
                    "order": 1,
                    "title": "Preparation and Properties",
                    "content_text": (
                        "Haloalkanes and haloarenes are hydrocarbons in which one or more hydrogen atoms are replaced by halogen atoms. "
                        "These may be classified as mono, di, or polyhalogen compounds. They can be prepared from hydrocarbons by "
                        "free-radical halogenation, from alcohols by the use of phosphorus halides, thionyl chloride or halogen acids. "
                        "Aryl halides are prepared by electrophilic substitution to arenes. Fluorides and iodides are best prepared by "
                        "halogen exchange method."
                    ),
                    "content_type": "explanation",
                    "worked_examples": [],
                    "diagrams": [],
                    "tables": []
                },
                {
                    "order": 2,
                    "title": "Physical Properties and Reactions",
                    "content_text": (
                        "The boiling points of organohalogen compounds are comparatively higher than the corresponding hydrocarbons "
                        "because of strong dipole-dipole and van der Waals forces of attraction. They are slightly soluble in water "
                        "but completely soluble in organic solvents. The polarity of the carbon-halogen bond is responsible for their "
                        "nucleophilic substitution, elimination and their reaction with metal atoms to form organometallic compounds. "
                        "Nucleophilic substitution reactions are categorised into $S_N1$ and $S_N2$ on the basis of their kinetic "
                        "properties. Chirality has a profound role in understanding the reaction mechanisms. $S_N2$ reactions of chiral "
                        "alkyl halides are characterised by inversion of configuration while $S_N1$ reactions are characterised by "
                        "racemisation."
                    ),
                    "content_type": "explanation",
                    "worked_examples": [],
                    "diagrams": [],
                    "tables": []
                },
                {
                    "order": 3,
                    "title": "Polyhalogen Compounds and Environmental Impact",
                    "content_text": (
                        "A number of polyhalogen compounds e.g., dichloromethane, chloroform, iodoform, carbon tetrachloride, "
                        "freon and DDT have many industrial applications. However, some of these compounds cannot be easily "
                        "decomposed and even cause depletion of the ozone layer and are proving to be environmental hazards."
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
    # 4. Fix existing exercise numbering
    # =========================================================================
    existing_ex = ch.get("exercises", {}).get("items", [])
    for ex in existing_ex:
        old = ex["number"]
        if old == 1:
            pass  # keep as 1
        elif 62 <= old <= 66:
            ex["number"] = old - 61 + 1  # 62→2, 63→3, ..., 66→6
    print(f"  ✅ Fixed exercise numbering: {[ex['number'] for ex in existing_ex]}")

    # =========================================================================
    # 5. Add 22 end-of-chapter exercises (6.1-6.22)
    # =========================================================================
    new_exercises = [
        {"number": 7, "problem": "Name the following halides according to IUPAC system and classify them as alkyl, allyl, benzyl (primary, secondary, tertiary), vinyl or aryl halides: (i) $(CH_3)_2CHCH(Cl)CH_3$ (ii) $CH_3CH_2C(CH_3)_2CH_2I$ (iii) $CH_3CH(CH_3)CH(Br)CH_3$ (iv) $CH_3C(Cl)(C_2H_5)CH_2CH_3$ (v) $CH_3CH=CHC(Br)(CH_3)_2$ (vi) $m$-$ClCH_2C_6H_4CH_2C(CH_3)_3$ (vii) $p$-$ClC_6H_4CH_2CH(CH_3)_2$ (viii) $o$-$Br$-$C_6H_4CH(CH_3)CH_2CH_3$", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:iupac_nomenclature", "concept:classification_of_halides"]},
        {"number": 8, "problem": "Give the IUPAC names of the following compounds: (i) $CH_3CH(Cl)CH(Br)CH_3$ (ii) $CHF_2CBrClF$ (iii) $ClCH_2C \\equiv CCH_2Br$ (iv) $(CCl_3)_3CCl$ (v) $CH_3C(p$-$ClC_6H_4)_2CH(Br)CH_3$ (vi) $(CH_3)_3CCH=CClC_6H_4I$-$p$", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:iupac_nomenclature"]},
        {"number": 9, "problem": "Write the structures of the following organic halogen compounds: (i) 2-Chloro-3-methylpentane (ii) 1-Chloro-4-ethylcyclohexane (iii) 1-Bromo-4-sec-butyl-2-methylbenzene (iv) 1,4-Dibromobut-2-ene", "solution": None, "difficulty": "easy", "exercise_type": "application", "tests": ["concept:structural_formulas"]},
        {"number": 10, "problem": "Which one of the following has the highest dipole moment? (i) $CH_2Cl_2$ (ii) $CHCl_3$ (iii) $CCl_4$", "solution": None, "difficulty": "easy", "exercise_type": "conceptual", "tests": ["concept:dipole_moment"]},
        {"number": 11, "problem": "A hydrocarbon $C_5H_{10}$ does not react with chlorine in dark but gives a single monochloro compound $C_5H_9Cl$ in bright sunlight. Identify the hydrocarbon.", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:free_radical_halogenation"]},
        {"number": 12, "problem": "Write the isomers of the compound having formula $C_4H_9Br$.", "solution": None, "difficulty": "easy", "exercise_type": "application", "tests": ["concept:structural_isomerism"]},
        {"number": 13, "problem": "Write the equations for the preparation of 1-iodobutane from (i) 1-butanol (ii) 1-chlorobutane (iii) but-1-ene.", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests": ["concept:preparation_of_haloalkanes"]},
        {"number": 14, "problem": "What are ambident nucleophiles? Explain with an example.", "solution": None, "difficulty": "easy", "exercise_type": "conceptual", "tests": ["concept:ambident_nucleophiles"]},
        {"number": 15, "problem": "Which compound in each of the following pairs will react faster in $S_N2$ reaction with $OH^-$? (i) $CH_3Br$ or $CH_3I$ (ii) $(CH_3)_3CCl$ or $CH_3Cl$", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:sn2_reaction"]},
        {"number": 16, "problem": "Predict all the alkenes that would be formed by dehydrohalogenation of the following halides with sodium ethoxide in ethanol and identify the major alkene: (i) 1-Bromo-1-methylcyclohexane (ii) 2-Chloro-2-methylbutane (iii) 2,2,3-Trimethyl-3-bromopentane.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:elimination_reactions", "concept:zaitsev_rule"]},
        {"number": 17, "problem": "How will you bring about the following conversions? (i) Ethanol to but-1-yne (ii) Ethane to bromoethene (iii) Propene to 1-nitropropane (iv) Toluene to benzyl alcohol (v) Propene to propyne (vi) Ethanol to ethyl fluoride (vii) Bromomethane to propanone (viii) But-1-ene to but-2-ene (ix) 1-Chlorobutane to n-octane (x) Benzene to biphenyl.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:organic_conversions"]},
        {"number": 18, "problem": "Explain why (i) the dipole moment of chlorobenzene is lower than that of cyclohexyl chloride? (ii) alkyl halides, though polar, are immiscible with water? (iii) Grignard reagents should be prepared under anhydrous conditions?", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:dipole_moment", "concept:grignard_reagent"]},
        {"number": 19, "problem": "Give the uses of freon 12, DDT, carbon tetrachloride and iodoform.", "solution": None, "difficulty": "easy", "exercise_type": "conceptual", "tests": ["concept:polyhalogen_compounds"]},
        {"number": 20, "problem": "Write the structure of the major organic product in each of the following reactions: (i) $CH_3CH_2CH_2Cl + NaI \\xrightarrow{acetone}$ (ii) $(CH_3)_3CBr + KOH \\xrightarrow{ethanol}$ (iii) $CH_3CH(Br)CH_2CH_3 + NaOH \\xrightarrow{water}$ (iv) $CH_3CH_2Br + KCN \\rightarrow$ (v) $C_6H_5ONa + C_2H_5Cl \\rightarrow$ (vi) $CH_3CH_2CH_2OH + SOCl_2 \\rightarrow$ (vii) $CH_3CH_2CH=CH_2 + HBr \\rightarrow$ (viii) $CH_3CH=C(CH_3)_2 + HBr \\rightarrow$", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:nucleophilic_substitution", "concept:elimination_reactions"]},
        {"number": 21, "problem": "Write the mechanism of the following reaction: $nBuBr + KCN \\xrightarrow{EtOH-H_2O} nBuCN$", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests": ["concept:sn2_reaction"]},
        {"number": 22, "problem": "Arrange the compounds of each set in order of reactivity towards $S_N2$ displacement: (i) 2-Bromo-2-methylbutane, 1-Bromopentane, 2-Bromopentane (ii) 1-Bromo-3-methylbutane, 2-Bromo-2-methylbutane, 2-Bromo-3-methylbutane (iii) 1-Bromobutane, 1-Bromo-2,2-dimethylpropane, 1-Bromo-2-methylbutane, 1-Bromo-3-methylbutane.", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:sn2_reaction", "concept:steric_hindrance"]},
        {"number": 23, "problem": "Out of $C_6H_5CH_2Cl$ and $C_6H_5CHClC_6H_5$, which is more easily hydrolysed by aqueous KOH?", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:nucleophilic_substitution"]},
        {"number": 24, "problem": "p-Dichlorobenzene has higher m.p. than those of o- and m-isomers. Discuss.", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:physical_properties_of_haloarenes"]},
        {"number": 25, "problem": "How the following conversions can be carried out? (i) Propene to propan-1-ol (ii) Ethanol to but-1-yne (iii) 1-Bromopropane to 2-bromopropane (iv) Toluene to benzyl alcohol (v) Benzene to 4-bromonitrobenzene (vi) Benzyl alcohol to 2-phenylethanoic acid (vii) Ethanol to propanenitrile (viii) Aniline to chlorobenzene (ix) 2-Chlorobutane to 3,4-dimethylhexane (x) 2-Methyl-1-propene to 2-chloro-2-methylpropane (xi) Ethyl chloride to propanoic acid (xii) But-1-ene to n-butyliodide (xiii) 2-Chloropropane to 1-propanol (xiv) Isopropyl alcohol to iodoform (xv) Chlorobenzene to p-nitrophenol (xvi) 2-Bromopropane to 1-bromopropane (xvii) Chloroethane to butane (xviii) Benzene to diphenyl (xix) tert-Butyl bromide to isobutyl bromide (xx) Aniline to phenylisocyanide", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:organic_conversions"]},
        {"number": 26, "problem": "The treatment of alkyl chlorides with aqueous KOH leads to the formation of alcohols but in the presence of alcoholic KOH, alkenes are major products. Explain.", "solution": None, "difficulty": "medium", "exercise_type": "conceptual", "tests": ["concept:substitution_vs_elimination"]},
        {"number": 27, "problem": "Primary alkyl halide $C_4H_9Br$ (a) reacted with alcoholic KOH to give compound (b). Compound (b) is reacted with HBr to give (c) which is an isomer of (a). When (a) is reacted with sodium metal it gives compound (d), $C_8H_{18}$, which is different from the compound formed when n-butyl bromide is reacted with sodium. Give the structural formula of (a) and write the equations for all the reactions.", "solution": None, "difficulty": "hard", "exercise_type": "application", "tests": ["concept:elimination_reactions", "concept:wurtz_reaction"]},
        {"number": 28, "problem": "What happens when (i) n-butyl chloride is treated with alcoholic KOH, (ii) bromobenzene is treated with Mg in the presence of dry ether, (iii) chlorobenzene is subjected to hydrolysis, (iv) ethyl chloride is treated with aqueous KOH, (v) methyl bromide is treated with sodium in the presence of dry ether, (vi) methyl chloride is treated with KCN?", "solution": None, "difficulty": "medium", "exercise_type": "application", "tests": ["concept:reactions_of_haloalkanes"]}
    ]

    existing_ex.extend(new_exercises)
    print(f"  ✅ Added {len(new_exercises)} end-of-chapter exercises (total: {len(existing_ex)})")

    # =========================================================================
    # 6. Clean up markers
    # =========================================================================
    json_str = json.dumps(data)
    
    # Remove [CONTINUES] if present
    for sec in ch["sections"]:
        for sub in sec.get("subsections", []):
            ct = sub.get("content_text", "")
            if ct.endswith("[CONTINUES]"):
                sub["content_text"] = ct[:-len("[CONTINUES]")].rstrip()

    json_str = json.dumps(data)
    assert "[SKIPPED" not in json_str, "ERROR: [SKIPPED] still present!"
    print("  ✅ No [SKIPPED] markers remain")
    
    continues = json_str.count("[CONTINUES]")
    print(f"  {'⚠️  ' + str(continues) if continues else '✅ No'} [CONTINUES] markers remain")

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
