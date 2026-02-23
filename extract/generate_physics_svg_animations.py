"""
Two-phase SVG animation generator for physics concepts.

Generates SVG+CSS animations (not Three.js) for physics concepts.
Uses existing Three.js prompts as context but regenerates for SVG format.

Phase 1: Generate SVG-specific prompts using Gemini (fast model)
Phase 2: Use those prompts to generate self-contained HTML files with SVG animations

Output:
  data/physics_svg_animations/prompts/  — saved prompts (JSON) for each concept
  data/physics_svg_animations/          — final HTML files with inline SVG animations

Usage:
    # Phase 1: Generate prompts for all concepts
    uv run python extract/generate_physics_svg_animations.py prompts

    # Phase 2: Generate SVG animations from prompts
    uv run python extract/generate_physics_svg_animations.py animations

    # Both phases for specific concepts
    uv run python extract/generate_physics_svg_animations.py prompts coulombs_law projectile_motion
    uv run python extract/generate_physics_svg_animations.py animations coulombs_law projectile_motion

    # Resume (skip already-done)
    uv run python extract/generate_physics_svg_animations.py prompts --resume
    uv run python extract/generate_physics_svg_animations.py animations --resume
"""

import json
import os
import sys
import time
import glob

from pathlib import Path
from google import genai

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANIMATIONS_DIR = Path("data/animations")
PROMPTS_DIR = Path("data/physics_svg_animations/prompts")
CLASSIFICATIONS_FILE = Path("data/concept_classifications.json")

# Models
PROMPT_MODEL = "gemini-3-flash-preview"     # Fast model for prompt generation
ANIMATION_MODEL = "gemini-3.1-pro-preview"  # Best model for code generation

# Load env
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")


# ---------------------------------------------------------------------------
# Get physics concepts
# ---------------------------------------------------------------------------

def get_physics_concepts() -> list[str]:
    """Get all physics concepts from the classifications file."""
    with open(CLASSIFICATIONS_FILE) as f:
        cls = json.load(f)
    return cls["clean_concepts"]


# ---------------------------------------------------------------------------
# Concept context builder (searches physics JSONs)
# ---------------------------------------------------------------------------

def get_concept_context(concept_name: str) -> dict:
    """Gather context about a concept from all physics JSONs."""
    files = sorted(f for f in glob.glob("data/ncert_physics_*.json")
                   if ".raw." not in f and ".progress." not in f)

    context = {
        "concept": concept_name,
        "appears_in": [],
        "related_content": [],
    }
    concept_ref = f"concept:{concept_name}"

    for fp in files:
        d = json.load(open(fp))
        ch = d["chapter"]
        grade = d["grade"]

        for s in ch.get("sections", []):
            prereq_match = any(
                p.get("ref") == concept_ref
                for p in s.get("prerequisites", [])
                if p.get("type") == "concept"
            )
            if prereq_match:
                context["appears_in"].append({
                    "grade": grade,
                    "chapter": ch["title"],
                    "section": f"{s['number']}: {s['title']}",
                })
                for sub in s.get("subsections", [])[:2]:
                    text = sub.get("content_text", "")[:300]
                    if text:
                        context["related_content"].append(text)

    return context


# ---------------------------------------------------------------------------
# Phase 1: Generate concept-specific SVG animation prompts
# ---------------------------------------------------------------------------

META_PROMPT = """You are a PhD physicist and visual designer creating a detailed specification for an animated SVG diagram.

## Concept: {display_name}

{where_used}

{content_snippets}

## Your Task:
Write a DETAILED, SPECIFIC prompt that will be sent to another AI to generate a self-contained HTML file with an **animated SVG diagram** for the concept "{display_name}".

This is for a PHYSICS concept. The animation should focus on force diagrams, motion paths, field lines, wave patterns, circuit diagrams, energy level diagrams, or physical process visualizations as appropriate.

Your prompt must specify EXACTLY:

### 1. What to Visualize
- What SVG elements to create (arrows for forces/vectors, circles for particles/charges, paths for trajectories, lines for field lines/rays, rectangles for blocks/components, etc.)
- What each element represents physically
- The exact colors for each element
- How elements should animate (motion, oscillation, field changes, wave propagation, etc.)
- Use CSS animations and SVG animate elements — NO JavaScript libraries needed

### 2. Animation Sequence
- Describe the step-by-step animation flow
- Specify timing (duration of each step, delays between steps)
- Whether the animation loops or plays once
- Key visual states (initial, intermediate, final)

### 3. Labels and Annotations
- What text labels to include (force names, variable values, units, etc.)
- Where to position labels relative to the SVG elements
- Use proper physics notation: vectors with arrows, subscripts, superscripts
- Include a title card explaining what the animation shows

### 4. Visual Layout Specifications
- Bright, clean background (#f8f9fa or white)
- Vibrant, saturated colors that distinguish different physical quantities
- Color scheme by category:
  - Forces: Red (#FF3366) for applied, Blue (#4361EE) for reaction, Green (#06D6A0) for velocity
  - Fields: Purple (#7209B7) for magnetic, Orange (#F77F00) for electric, Cyan (#00B4D8) for gravitational
  - Energy: Red for kinetic, Blue for potential, Green for total
  - Waves: gradient colors showing amplitude variation
- Google Fonts: Inter for labels, Roboto Mono for values/formulas
- Clean, centered SVG with adequate padding
- 800x500px default viewBox, responsive scaling

### 5. Physics Accuracy Checklist
- List the specific physics rules this animation MUST follow
- Correct vector directions, magnitudes, and sign conventions
- Proper proportionalities (F ∝ 1/r², etc.)
- Standard conventions (right-hand rule, positive directions, etc.)

### 6. Technical Requirements
- Self-contained HTML with inline SVG
- CSS animations only (keyframes, transitions). Minimal JavaScript only if needed for interactivity.
- Responsive: SVG scales with viewport using viewBox
- Accessible: include aria-labels for key elements
- No external assets (fonts via Google Fonts CDN only)

## Output Format:
Write the prompt as a clear, numbered specification document. Be extremely specific about the physics — leave nothing ambiguous.
"""


def build_meta_prompt(concept_name: str, context: dict) -> str:
    """Build the meta-prompt for generating a concept-specific SVG animation prompt."""
    display_name = concept_name.replace("_", " ").title()

    where_used = ""
    if context["appears_in"]:
        sections = [f"  - Class {a['grade']}: {a['chapter']} → {a['section']}"
                    for a in context["appears_in"][:5]]
        where_used = "### Where This Concept Is Taught:\n" + "\n".join(sections)

    content_snippets = ""
    if context["related_content"]:
        snippets = [f"  > {s[:200]}..." for s in context["related_content"][:3]]
        content_snippets = "### Related Textbook Content:\n" + "\n".join(snippets)

    return META_PROMPT.format(
        display_name=display_name,
        where_used=where_used,
        content_snippets=content_snippets,
    )


def generate_prompt(concept_name: str, max_retries: int = 3) -> str:
    """Phase 1: Generate a concept-specific SVG animation prompt."""
    context = get_concept_context(concept_name)
    meta_prompt = build_meta_prompt(concept_name, context)

    client = genai.Client(api_key=API_KEY)
    backoff = [10, 20, 40]

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=PROMPT_MODEL,
                contents=[meta_prompt],
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 8192,
                },
            )
            if response.text is None:
                raise ValueError("Empty response")
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if any(k in err for k in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "Empty response")) and attempt < max_retries:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"\n    ⏳ Retry in {wait}s: {err[:100]}")
                time.sleep(wait)
                continue
            raise


# ---------------------------------------------------------------------------
# Phase 2: Generate SVG animation HTML from prompt
# ---------------------------------------------------------------------------

ANIMATION_WRAPPER = """You are an expert SVG artist and physicist. Generate a SINGLE, self-contained HTML file with an animated SVG diagram based on the following specification.

## CRITICAL RULES:
1. Output ONLY raw HTML starting with <!DOCTYPE html>. No markdown fences, no explanations.
2. The animation MUST be physically accurate — a student will learn from this.
3. Use inline SVG — no external SVG files.
4. CSS animations only (keyframes, transitions). Minimal JavaScript only if needed for interactivity (e.g., play/pause button, step-through).
5. Self-contained — no external images. Fonts loaded via Google Fonts CDN only.
6. Responsive: SVG scales with viewport using viewBox.
7. BRIGHT, LIGHT background (#f8f9fa or white). NOT dark theme.
8. Vibrant, physically-meaningful colors:
   - Forces: Red (#FF3366), Blue (#4361EE), Green (#06D6A0)
   - Fields: Purple (#7209B7) magnetic, Orange (#F77F00) electric, Cyan (#00B4D8) gravitational
   - Energy: Red=kinetic, Blue=potential, Green=total
   - Vectors: bold colored arrows with proper arrowheads
   - Particles: filled circles with appropriate colors
9. Include a title at the top of the page explaining the concept.
10. The SVG should be at least 800x500 viewBox, centered on the page.
11. Use Google Fonts (Inter for text, Roboto Mono for formulas).
12. Include a subtle legend or key if multiple colors/symbols are used.
13. Animation should loop smoothly with appropriate easing.

## SVG Animation Specification:
{concept_prompt}

## Output:
Generate the complete HTML file now. Start with <!DOCTYPE html>."""


def generate_animation(concept_name: str, concept_prompt: str, max_retries: int = 3) -> str:
    """Phase 2: Generate SVG animation HTML from a concept-specific prompt."""
    full_prompt = ANIMATION_WRAPPER.format(concept_prompt=concept_prompt)

    client = genai.Client(api_key=API_KEY)
    backoff = [15, 30, 60]

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=ANIMATION_MODEL,
                contents=[full_prompt],
                config={
                    "temperature": 0.4,
                    "max_output_tokens": 65536,
                },
            )
            if response.text is None:
                raise ValueError("Empty response")

            html = response.text.strip()

            # Strip markdown code fences if present
            if html.startswith("```"):
                lines = html.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                html = "\n".join(lines)

            # Validate
            if "<html" not in html.lower() and "<!doctype" not in html.lower():
                raise ValueError("Response doesn't look like HTML")
            if "<svg" not in html.lower():
                raise ValueError("Response doesn't include SVG")

            return html

        except Exception as e:
            err = str(e)
            if any(k in err for k in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "Empty response")) and attempt < max_retries:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"\n    ⏳ Retry in {wait}s: {err[:100]}")
                time.sleep(wait)
                continue
            raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    phase = sys.argv[1]  # "prompts" or "animations"
    resume = "--resume" in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith("--")]

    if args:
        concepts = [a if a.startswith("concept:") else f"concept:{a}" for a in args]
    else:
        concepts = get_physics_concepts()

    # Ensure dirs exist
    ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    if phase == "prompts":
        run_phase1(concepts, resume)
    elif phase == "animations":
        run_phase2(concepts, resume)
    else:
        print(f"Unknown phase: {phase}. Use 'prompts' or 'animations'.")


def run_phase1(concepts: list, resume: bool):
    """Phase 1: Generate concept-specific SVG animation prompts."""
    print(f"📝 Phase 1: Generating SVG animation prompts for physics")
    print(f"   Model: {PROMPT_MODEL}")
    print(f"   Concepts: {len(concepts)}")
    print(f"   Output: {PROMPTS_DIR}/")
    print(f"{'='*60}\n")

    results = {"success": 0, "skipped": 0, "failed": 0, "errors": []}

    for i, concept in enumerate(concepts, 1):
        name = concept.replace("concept:", "")
        display = name.replace("_", " ").title()
        out_file = PROMPTS_DIR / f"{name}.json"

        if resume and out_file.exists():
            print(f"  [{i}/{len(concepts)}] ⏭️  {display}")
            results["skipped"] += 1
            continue

        print(f"  [{i}/{len(concepts)}] 📝 {display}... ", end="", flush=True)

        try:
            prompt_text = generate_prompt(name)
            out_file.write_text(json.dumps({
                "concept": name,
                "prompt": prompt_text,
            }, indent=2))
            print(f"✅ ({len(prompt_text)} chars)")
            results["success"] += 1
        except Exception as e:
            print(f"❌ {e}")
            results["failed"] += 1
            results["errors"].append({"concept": name, "error": str(e)})

        if i < len(concepts):
            time.sleep(1)

    print_summary(results, PROMPTS_DIR / "phase1_log.json")


def run_phase2(concepts: list, resume: bool):
    """Phase 2: Generate SVG animation HTML from saved prompts."""
    print(f"🎨 Phase 2: Generating SVG animations for physics")
    print(f"   Model: {ANIMATION_MODEL}")
    print(f"   Concepts: {len(concepts)}")
    print(f"   Output: {ANIMATIONS_DIR}/")
    print(f"{'='*60}\n")

    results = {"success": 0, "skipped": 0, "failed": 0, "errors": []}

    for i, concept in enumerate(concepts, 1):
        name = concept.replace("concept:", "")
        display = name.replace("_", " ").title()
        prompt_file = PROMPTS_DIR / f"{name}.json"
        out_file = ANIMATIONS_DIR / f"{name}.html"

        if resume and out_file.exists():
            print(f"  [{i}/{len(concepts)}] ⏭️  {display}")
            results["skipped"] += 1
            continue

        if not prompt_file.exists():
            print(f"  [{i}/{len(concepts)}] ⚠️  {display} — no prompt (run phase 1 first)")
            results["failed"] += 1
            results["errors"].append({"concept": name, "error": "No prompt file"})
            continue

        print(f"  [{i}/{len(concepts)}] 🎨 {display}... ", end="", flush=True)

        try:
            prompt_data = json.loads(prompt_file.read_text())
            concept_prompt = prompt_data["prompt"]

            html = generate_animation(name, concept_prompt)

            out_file.write_text(html)
            size_kb = len(html) / 1024
            print(f"✅ ({size_kb:.0f}KB)")
            results["success"] += 1

        except Exception as e:
            print(f"❌ {e}")
            results["failed"] += 1
            results["errors"].append({"concept": name, "error": str(e)})

        if i < len(concepts):
            time.sleep(3)

    print_summary(results, ANIMATIONS_DIR / "phase2_log.json")


def print_summary(results: dict, log_file: Path):
    print(f"\n{'='*60}")
    print(f"✅ Success: {results['success']}")
    print(f"⏭️  Skipped: {results['skipped']}")
    print(f"❌ Failed:  {results['failed']}")
    if results["errors"]:
        print(f"\nFailed concepts:")
        for e in results["errors"]:
            print(f"  {e['concept']}: {e['error'][:100]}")
    print(f"{'='*60}")

    with open(log_file, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
