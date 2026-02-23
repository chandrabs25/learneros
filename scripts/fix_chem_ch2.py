"""
Fix ncert_chemistry_11_ch2.json:
1. Fix garbled black-body radiation text in section 2.3.2 subsection 2
2. Complete truncated Example 2.9 solution in section 2.3.3
3. Add missing "Dual Behaviour of Electromagnetic Radiation" subsection
4. Move misplaced spectra subsections (6-11) from 2.3.3 into new section 2.3.4
"""

import json
import sys
from pathlib import Path

JSON_PATH = Path("data/ncert_chemistry_11_ch2.json")

def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    sections = data["chapter"]["sections"]

    # =========================================================================
    # 1. Fix Black-body Radiation subsection in section 2.3.2
    # =========================================================================
    sec_232 = next(s for s in sections if s["number"] == "2.3.2")
    bb_sub = next(sub for sub in sec_232["subsections"] if sub["order"] == 2)
    
    bb_sub["content_text"] = (
        "It is noteworthy that the first concrete explanation for the phenomenon "
        "of the black body radiation was given by Max Planck in 1900. "
        "Hot objects emit electromagnetic radiations over a wide range of wavelengths. "
        "At high temperatures, an appreciable proportion of radiation is in the visible "
        "region of the spectrum. As the temperature is raised, a higher proportion of "
        "short wavelength (blue light) is generated. For example, when an iron rod is "
        "heated in a furnace, it first turns to dull red and then progressively becomes "
        "more and more red as the temperature increases. As this is heated further, the "
        "radiation emitted becomes white and then becomes blue as the temperature becomes "
        "very high. This means that red radiation is most intense at a particular "
        "temperature and the blue radiation is more intense at another temperature. "
        "This means intensities of radiations of different wavelengths emitted by hot "
        "body depend upon its temperature. "
        "By late 1850's it was known that objects made of different material and kept "
        "at different temperatures emit different amount of radiation. Also, when the "
        "surface of an object is irradiated with light (electromagnetic radiation), a "
        "part of radiant energy is generally reflected as such, a part is absorbed and "
        "a part of it is transmitted. The reason for incomplete absorption is that "
        "ordinary objects are as a rule imperfect absorbers of radiation. An ideal body, "
        "which emits and absorbs radiations of all frequencies uniformly, is called a "
        "black body and the radiation emitted by such a body is called black body "
        "radiation. "
        "In practice, no such body exists. Carbon black approximates fairly closely "
        "to black body. A good physical approximation to a black body is a cavity with "
        "a tiny hole, which has no other opening. Any ray entering the hole will be "
        "reflected by the cavity walls and will be eventually absorbed by the walls. "
        "A black body is also a perfect radiator of radiant energy. Furthermore, a "
        "black body is in thermal equilibrium with its surroundings. It radiates same "
        "amount of energy per unit area as it absorbs from its surrounding in any "
        "given time. "
        "The amount of light emitted (intensity of radiation) from a black body and "
        "its spectral distribution depends only on its temperature. At a given "
        "temperature, intensity of radiation emitted increases with the increase of "
        "wavelength, reaches a maximum value at a given wavelength and then starts "
        "decreasing with further increase of wavelength, as shown in Fig. 2.8. Also, "
        "as the temperature increases, maxima of the curve shifts to short wavelength. "
        "Several attempts were made to predict the intensity of radiation as a function "
        "of wavelength. But the results of the above experiment could not be explained "
        "satisfactorily on the basis of the wave theory of light. Max Planck arrived "
        "at a satisfactory relationship by making an assumption that absorption and "
        "emission of radiation arises from oscillators, i.e., atoms in the wall of "
        "black body. Their frequency of oscillation is changed by interaction with "
        "oscillators of electromagnetic radiation. Planck assumed that radiation could "
        "be sub-divided into discrete chunks of energy. He suggested that atoms and "
        "molecules could emit or absorb energy only in discrete quantities and not in "
        "a continuous manner. He gave the name quantum to the smallest quantity of "
        "energy that can be emitted or absorbed in the form of electromagnetic radiation."
    )
    print("  ✅ Fixed black-body radiation content_text in 2.3.2 subsection 2")

    # =========================================================================
    # 2. Fix truncated Example 2.9 solution in section 2.3.3
    # =========================================================================
    sec_233 = next(s for s in sections if s["number"] == "2.3.3")
    ex29_sub = next(sub for sub in sec_233["subsections"] if sub["order"] == 5)
    
    ex29_sub["worked_examples"][0]["solution"] = (
        "According to Einstein's equation, Kinetic energy = "
        "$\\frac{1}{2}m_e v^2 = h(\\nu - \\nu_0)$. "
        "$= (6.626 \\times 10^{-34} \\text{ J s}) \\times "
        "(1.0 \\times 10^{15} \\text{ s}^{-1} - 7.0 \\times 10^{14} \\text{ s}^{-1})$ "
        "$= (6.626 \\times 10^{-34} \\text{ J s}) \\times (3.0 \\times 10^{14} \\text{ s}^{-1})$ "
        "$= 1.988 \\times 10^{-19}$ J."
    )
    print("  ✅ Fixed truncated Example 2.9 solution in 2.3.3 subsection 5")

    # =========================================================================
    # 3. Add "Dual Behaviour of Electromagnetic Radiation" subsection
    #    AND move misplaced subsections 6-11 to a new section 2.3.4
    # =========================================================================

    # Separate photoelectric subsections (1-5) from misplaced spectra subsections (6-11)
    photo_subsections = [s for s in sec_233["subsections"] if s["order"] <= 5]
    spectra_subsections = [s for s in sec_233["subsections"] if s["order"] >= 6]

    # Add "Dual Behaviour" as new subsection 6 in the photoelectric section
    dual_behaviour_sub = {
        "order": 6,
        "title": "Dual Behaviour of Electromagnetic Radiation",
        "content_text": (
            "The particle nature of light posed a dilemma for scientists. On the one "
            "hand, it could explain the black body radiation and photoelectric effect "
            "satisfactorily but on the other hand, it was not consistent with the known "
            "wave behaviour of light which could account for the phenomena of interference "
            "and diffraction. The only way to resolve the dilemma was to accept the idea "
            "that light possesses both particle and wave-like properties, i.e., light has "
            "dual behaviour. Depending on the experiment, we find that light behaves "
            "either as a wave or as a stream of particles. Whenever radiation interacts "
            "with matter, it displays particle like properties in contrast to the wavelike "
            "properties (interference and diffraction), which it exhibits when it "
            "propagates. This concept was totally alien to the way the scientists thought "
            "about matter and radiation and it took them a long time to become convinced "
            "of its validity. It turns out, as you shall see later, that some microscopic "
            "particles like electrons also exhibit this wave-particle duality."
        ),
        "content_type": "explanation",
        "worked_examples": [],
        "diagrams": [],
        "tables": []
    }
    photo_subsections.append(dual_behaviour_sub)

    # Update section 2.3.3 with only photoelectric + dual behaviour subsections
    sec_233["subsections"] = photo_subsections
    print("  ✅ Added 'Dual Behaviour of EM Radiation' as subsection 6 in 2.3.3")

    # =========================================================================
    # 4. Create new section 2.3.4 for atomic spectra content
    # =========================================================================

    # Renumber the spectra subsections starting from 1
    for i, sub in enumerate(spectra_subsections, start=1):
        sub["order"] = i

    new_section = {
        "number": "2.3.4",
        "title": "Evidence for the Quantized Electronic Energy Levels: Atomic Spectra",
        "content_text": None,
        "subsections": spectra_subsections,
        "prerequisites": [
            {
                "type": "section",
                "ref": "ncert:chemistry:11:2:2.3.3"
            },
            {
                "type": "concept",
                "ref": "concept:quantization"
            }
        ]
    }

    # Insert the new section right after 2.3.3
    idx_233 = next(i for i, s in enumerate(sections) if s["number"] == "2.3.3")
    sections.insert(idx_233 + 1, new_section)
    print("  ✅ Created new section 2.3.4 with spectra subsections (moved from 2.3.3)")

    # =========================================================================
    # Save
    # =========================================================================
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved fixed JSON to {JSON_PATH}")
    print(f"   File size: {JSON_PATH.stat().st_size:,} bytes")

    # Quick validation
    with open(JSON_PATH) as f:
        json.load(f)  # Will raise if invalid
    print("   JSON validation: ✅ valid")


if __name__ == "__main__":
    main()
