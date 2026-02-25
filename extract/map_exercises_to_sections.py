"""
Map exercises to sections using Gemini.

For each chapter JSON, sends the section outline + exercise problems to Gemini
and asks it to assign each exercise to the most relevant section(s).
Updates the `tests` field with proper section IDs like:
    ncert:physics:11:9:9.4

Usage:
    # Process all physics files
    uv run python extract/map_exercises_to_sections.py

    # Process a single file
    uv run python extract/map_exercises_to_sections.py data/ncert_physics_11_ch9.json

    # Dry run (print mappings without writing)
    uv run python extract/map_exercises_to_sections.py --dry-run
"""

import json
import glob
import os
import sys
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()


# ---------------------------------------------------------------------------
# Gemini caller (text-only, structured JSON output)
# ---------------------------------------------------------------------------

MAPPING_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "mappings": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "exercise_number": {
                        "type": "INTEGER",
                        "description": "The exercise number",
                    },
                    "section_numbers": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "List of section number strings this exercise tests (e.g. ['9.4', '9.5'])",
                    },
                },
                "required": ["exercise_number", "section_numbers"],
            },
        },
    },
    "required": ["mappings"],
}


def call_gemini_text(prompt: str, max_retries: int = 5) -> dict:
    """Send a text-only prompt to Gemini and get structured JSON back."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    backoff = [10, 30, 60, 120, 240]

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": MAPPING_SCHEMA,
                    "temperature": 0.1,
                },
            )
            if response.text is None:
                raise ValueError(f"Empty response from Gemini")
            return json.loads(response.text)
        except Exception as e:
            err = str(e)
            retryable = any(k in err for k in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if retryable and attempt < max_retries:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"  ⏳ Retry in {wait}s: {err[:200]}")
                time.sleep(wait)
                continue
            raise


# ---------------------------------------------------------------------------
# Build the prompt
# ---------------------------------------------------------------------------

def build_section_outline(chapter: dict) -> str:
    """Build a concise section outline with titles and key topics."""
    lines = []
    for s in chapter.get("sections", []):
        # Skip non-content sections
        if s["number"] in ("Summary", "Points to Ponder"):
            continue

        sub_titles = []
        for sub in s.get("subsections", []):
            title = sub["title"]
            # Include worked example labels if any
            we_labels = [w["label"] for w in sub.get("worked_examples", [])]
            if we_labels:
                title += f" [{', '.join(we_labels)}]"
            sub_titles.append(title)

        lines.append(f"Section {s['number']}: {s['title']}")
        if sub_titles:
            for st in sub_titles:
                lines.append(f"  - {st}")

    return "\n".join(lines)


def build_exercise_list(chapter: dict) -> str:
    """Build a list of exercises with their problem text."""
    ex_items = ((chapter.get("exercises") or {}).get("items") or [])
    lines = []
    for e in ex_items:
        # Truncate very long problems to avoid token waste
        problem = e["problem"]
        if len(problem) > 400:
            problem = problem[:400] + "..."
        lines.append(f"Exercise {e['number']}: {problem}")
    return "\n\n".join(lines)


def build_mapping_prompt(data: dict) -> str:
    """Build the full prompt for exercise-to-section mapping."""
    ch = data["chapter"]
    subject = data["subject"]
    grade = data["grade"]
    ch_num = ch["number"]
    ch_title = ch["title"]

    section_outline = build_section_outline(ch)
    exercise_list = build_exercise_list(ch)

    # Build explicit list of valid section numbers
    valid_nums = []
    for s in ch.get("sections", []):
        if s["number"] not in ("Summary", "Points to Ponder"):
            valid_nums.append(s["number"])
    valid_list = ", ".join(f'"{n}"' for n in valid_nums)

    return f"""You are an expert {subject} teacher analyzing a Class {grade} NCERT textbook.

## Chapter {ch_num}: {ch_title}

### Section Outline:
{section_outline}

### Exercises:
{exercise_list}

## Task:
For EACH exercise, determine which TOP-LEVEL section(s) of this chapter it primarily tests.

## CRITICAL RULES:
- You MUST ONLY use these exact section numbers: [{valid_list}]
- Do NOT invent subsection numbers like "{ch_num}.2.2" or "{ch_num}.4.1" — only use the top-level section numbers listed above.
- Assign 1-2 sections per exercise (the most relevant ones).
- Base your mapping on which section teaches the concept needed to solve the exercise.

Return a JSON mapping for every exercise."""


# ---------------------------------------------------------------------------
# Process one file
# ---------------------------------------------------------------------------

def process_file(filepath: str, dry_run: bool = False) -> dict:
    """Map exercises to sections for a single JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    bn = os.path.basename(filepath)
    ch = data["chapter"]
    ex_items = ((ch.get("exercises") or {}).get("items") or [])

    if not ex_items:
        print(f"  ⏭️  {bn}: no exercises, skipping")
        return {"file": bn, "mapped": 0, "total": 0}

    # Build section ID prefix
    prefix = f"{data['curriculum']}:{data['subject']}:{data['grade']}"
    ch_num = ch["number"]

    # Get valid section numbers for this chapter
    valid_sections = {
        s["number"]
        for s in ch.get("sections", [])
        if s["number"] not in ("Summary", "Points to Ponder")
    }

    prompt = build_mapping_prompt(data)
    print(f"  🔍 {bn}: {len(ex_items)} exercises, {len(valid_sections)} sections... ", end="", flush=True)

    result = call_gemini_text(prompt)
    mappings = {m["exercise_number"]: m["section_numbers"] for m in result["mappings"]}

    # Apply mappings
    mapped = 0
    for e in ex_items:
        sections = mappings.get(e["number"], [])

        # Normalize: if Gemini returned a subsection (e.g. "9.2.2"),
        # strip it to the parent section ("9.2")
        normalized = []
        for s in sections:
            if s in valid_sections:
                normalized.append(s)
            else:
                # Try stripping last component: "9.2.2" → "9.2"
                parent = ".".join(s.split(".")[:2])
                if parent in valid_sections:
                    normalized.append(parent)
        # Deduplicate while preserving order
        seen = set()
        sections = []
        for s in normalized:
            if s not in seen:
                seen.add(s)
                sections.append(s)

        if sections:
            # Build proper section IDs: ncert:physics:11:9:9.4
            section_ids = [f"{prefix}:{ch_num}:{s}" for s in sections]
            e["tests"] = section_ids
            mapped += 1

    print(f"✅ {mapped}/{len(ex_items)} mapped")

    if dry_run:
        # Print mappings for review
        for e in ex_items:
            tc = e.get("tests", [])
            prob = e["problem"][:60].replace("\n", " ")
            print(f"    #{e['number']}: {tc} — {prob}...")
    else:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return {"file": bn, "mapped": mapped, "total": len(ex_items)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        files = args
    else:
        files = sorted(
            f for f in glob.glob("data/ncert_physics_*.json")
            if ".raw." not in f and ".progress." not in f
        )

    print(f"📦 Processing {len(files)} files {'(DRY RUN)' if dry_run else ''}\n")

    results = []
    for fp in files:
        try:
            r = process_file(fp, dry_run)
            results.append(r)
        except Exception as e:
            print(f"  ❌ {os.path.basename(fp)}: {e}")
            results.append({"file": os.path.basename(fp), "mapped": 0, "total": 0, "error": str(e)})
        time.sleep(2)  # Rate limit pause

    # Summary
    total_mapped = sum(r["mapped"] for r in results)
    total_ex = sum(r["total"] for r in results)
    errors = [r for r in results if "error" in r]

    print(f"\n{'='*50}")
    print(f"✅ Mapped {total_mapped}/{total_ex} exercises across {len(files)} files")
    if errors:
        print(f"❌ {len(errors)} files had errors")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
