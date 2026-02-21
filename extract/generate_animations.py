"""
Two-phase Three.js animation generator for physics concepts.

Phase 1: Generate concept-specific prompts using Gemini (fast model)
Phase 2: Use those prompts to generate self-contained HTML animations (Gemini 3 Pro)

Output:
  data/animations/prompts/  — saved prompts (JSON) for each concept
  data/animations/          — final HTML files

Usage:
    # Phase 1: Generate prompts for all concepts
    uv run python extract/generate_animations.py prompts

    # Phase 2: Generate HTML animations from prompts
    uv run python extract/generate_animations.py animations

    # Both phases for specific concepts
    uv run python extract/generate_animations.py prompts coulombs_law projectile_motion
    uv run python extract/generate_animations.py animations coulombs_law projectile_motion

    # Resume (skip already-done)
    uv run python extract/generate_animations.py animations --resume
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

ANIMATIONS_DIR = Path("data/animations2")
PROMPTS_DIR = Path("data/animations/prompts")  # Original prompts directory
CLASSIFICATIONS_FILE = Path("data/concept_classifications.json")

# Models
PROMPT_MODEL = "gemini-3-flash-preview"   # Fast model for prompt generation
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
# Concept context builder
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
# Phase 1: Generate concept-specific prompts
# ---------------------------------------------------------------------------

META_PROMPT = """You are a PhD physicist creating a detailed specification for a Three.js interactive 3D animation.

## Concept: {display_name}

{where_used}

{content_snippets}

## Your Task:
Write a DETAILED, SPECIFIC prompt that will be sent to another AI to generate a self-contained HTML file with an interactive Three.js 3D animation for the concept "{display_name}".

Your prompt must specify EXACTLY:

### 1. What to Visualize
- What 3D objects to create (spheres, arrows, planes, curves, particles, etc.)
- What each object represents physically
- The exact colors to use for each object (use bright, vibrant colors — this is a LIGHT-THEMED UI)
- How objects should move/animate and what physics equations govern the motion

### 2. What Parameters the Student Can Control
- List each slider/control with:
  - Label and variable name
  - Min, max, step, default value
  - Units (SI)
  - What changes visually when this slider moves

### 3. The Exact Formulas
- Write out every formula used in the animation
- Specify what each variable means
- Show how the formula connects slider values to visual output

### 4. Visual Layout Specifications
- Bright, clean background (#f0f4f8 or similar light color, NOT dark)
- Vibrant, saturated colorful objects that pop against the light background
- White/light glassmorphic control panel with colorful accents
- Color scheme: Red (#FF3366) for positive/high values, Blue (#4361EE) for negative/low, Green (#06D6A0) for velocity, Orange (#F77F00) for acceleration, Purple (#7209B7) for magnetic
- Google Fonts: Inter for UI, Roboto Mono for values
- 75% viewport for 3D scene, 25% for controls
- Formula card at top-left with live calculated values

### 5. Physics Accuracy Checklist
- List the specific physics rules this animation MUST follow
- List common mistakes that could occur for THIS specific concept and how to avoid them
- Specify correct vector directions, sign conventions, and proportionalities

### 6. Technical Requirements
- Self-contained HTML with Three.js r128 via CDN
- OrbitControls for camera
- Responsive layout, 60fps requestAnimationFrame loop
- HTML overlay labels (not 3D text)
- No external assets

## Output Format:
Write the prompt as a clear, numbered specification document. Be extremely specific — leave nothing ambiguous. The AI receiving this prompt should have zero physics questions.
"""


def build_meta_prompt(concept_name: str, context: dict) -> str:
    """Build the meta-prompt for generating a concept-specific animation prompt."""
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
    """Phase 1: Generate a concept-specific animation prompt."""
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
# Phase 2: Generate HTML animation from prompt
# ---------------------------------------------------------------------------

ANIMATION_WRAPPER = """You are an expert Three.js developer and physicist. Generate a SINGLE, self-contained HTML file based on the following specification.

## CRITICAL RULES:
1. Output ONLY raw HTML starting with <!DOCTYPE html>. No markdown fences, no explanations.
2. The animation MUST be physically accurate — a student will learn from this.
3. Use Three.js r128 via CDN: https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js
4. Include OrbitControls: https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js
5. Self-contained — no external images, fonts loaded via Google Fonts CDN only.
6. Responsive layout, 60fps animation loop.
7. BRIGHT, LIGHT background (#f0f4f8 or similar). NOT dark theme.
8. Vibrant, colorful objects with saturated colors that pop against the light background.
9. Control panel: white/light glassmorphic with subtle shadows and colorful slider accent colors.

## Animation Specification:
{concept_prompt}

## Output:
Generate the complete HTML file now. Start with <!DOCTYPE html>."""


def generate_animation(concept_name: str, concept_prompt: str, max_retries: int = 3) -> str:
    """Phase 2: Generate HTML animation from a concept-specific prompt."""
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
            if "three" not in html.lower():
                raise ValueError("Response doesn't include Three.js")

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

    # Load concept list
    with open(CLASSIFICATIONS_FILE) as f:
        cls = json.load(f)

    if args:
        concepts = [a if a.startswith("concept:") else f"concept:{a}" for a in args]
    else:
        concepts = cls["clean_concepts"]

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
    """Phase 1: Generate concept-specific prompts."""
    model = PROMPT_MODEL
    print(f"📝 Phase 1: Generating concept-specific prompts")
    print(f"   Model: {model}")
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
            time.sleep(1)  # Light rate limiting for flash

    print_summary(results, PROMPTS_DIR / "phase1_log.json")


def run_phase2(concepts: list, resume: bool):
    """Phase 2: Generate HTML animations from saved prompts."""
    model = ANIMATION_MODEL
    print(f"🎨 Phase 2: Generating Three.js animations")
    print(f"   Model: {model}")
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
            time.sleep(3)  # Heavier rate limiting for pro model

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
