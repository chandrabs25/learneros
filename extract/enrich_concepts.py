"""
Ensure every chapter has at least MIN_CONCEPTS concept prerequisites.

For chapters below the threshold, uses Gemini to suggest additional
cross-chapter concept prerequisites that a student would need.

Usage:
    uv run python extract/enrich_concepts.py              # all subjects
    uv run python extract/enrich_concepts.py --dry-run     # preview only
    uv run python extract/enrich_concepts.py data/ncert_physics_11_ch1.json  # single file
"""

import json
import glob
import os
import sys
import time
import re

from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

MIN_CONCEPTS = 5
MODEL = "gemini-2.5-flash"


def get_existing_concepts(data: dict) -> set[str]:
    """Get all concept refs already present in a chapter's section prerequisites."""
    concepts = set()
    for sec in data["chapter"].get("sections", []):
        for p in sec.get("prerequisites", []):
            if p.get("type") == "concept":
                concepts.add(p["ref"])
    return concepts


def build_section_overview(data: dict) -> str:
    """Build a text overview of the chapter sections."""
    ch = data["chapter"]
    lines = []
    for s in ch.get("sections", []):
        if s["number"] in ("Summary", "Points to Ponder"):
            continue
        sub_titles = [sub.get("title", "") for sub in s.get("subsections", [])[:5]]
        preview = ""
        subs = s.get("subsections", [])
        if subs:
            preview = (subs[0].get("content_text", "") or "")[:200]
        lines.append(f"Section {s['number']}: {s['title']}")
        if sub_titles:
            lines.append(f"  Subtopics: {', '.join(sub_titles)}")
        if preview:
            lines.append(f"  Preview: {preview}...")
    return "\n".join(lines)


def generate_concepts(data: dict, existing: set[str], needed: int) -> list[dict]:
    """Use Gemini to suggest concept prerequisites for undercounted chapters."""
    ch = data["chapter"]
    subject = data["subject"]
    grade = data["grade"]
    ch_num = ch["number"]

    section_overview = build_section_overview(data)
    existing_list = "\n".join(f"  - {c}" for c in sorted(existing)) if existing else "  (none)"

    prompt = f"""You are an expert {subject} teacher analyzing an NCERT Class {grade} textbook chapter.

## Chapter {ch_num}: {ch["title"]}

### Sections:
{section_overview}

### Existing concept prerequisites:
{existing_list}

## Task:
This chapter currently has only {len(existing)} concept prerequisites. We need at least {MIN_CONCEPTS}.

Suggest {needed} additional CROSS-CHAPTER concept prerequisites that a student would need to understand BEFORE studying this chapter. These should be foundational concepts from EARLIER chapters or from other subjects.

## Rules:
- Use snake_case names with "concept:" prefix (e.g., "concept:cell_division", "concept:newtons_laws")
- Each concept should be a genuine prerequisite that a student would need
- Don't duplicate existing concepts listed above
- For each concept, specify which section(s) of THIS chapter require it
- Prefer broad, foundational concepts over hyper-specific ones
- Concepts should represent knowledge from OUTSIDE this chapter

## Output Format (JSON array):
[
  {{"concept": "concept:example_name", "section": "1.2", "reason": "Brief reason"}},
  ...
]

Return ONLY the JSON array, no explanation."""

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=[prompt],
                config={"temperature": 0.2, "max_output_tokens": 4096},
            )
            if not response.text:
                raise ValueError("Empty response")

            # Parse JSON from response
            text = response.text.strip()
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError("No JSON array found in response")

        except Exception as e:
            err = str(e)
            if any(k in err for k in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                time.sleep(15 * (attempt + 1))
                continue
            raise

    return []


def process_file(filepath: str, dry_run: bool = False) -> dict:
    """Enrich a single file with additional concept prerequisites."""
    with open(filepath) as f:
        data = json.load(f)

    bn = os.path.basename(filepath)
    ch = data["chapter"]
    existing = get_existing_concepts(data)

    if len(existing) >= MIN_CONCEPTS:
        return {"file": bn, "existing": len(existing), "added": 0, "status": "ok"}

    needed = MIN_CONCEPTS - len(existing)
    print(f"  🔍 {bn}: {len(existing)} concepts, need {needed} more... ", end="", flush=True)

    suggestions = generate_concepts(data, existing, needed)

    # Apply suggestions to sections
    added = 0
    sections_map = {str(s["number"]): s for s in ch.get("sections", [])}

    for sug in suggestions:
        concept_ref = sug["concept"]
        target_section = str(sug.get("section", ""))

        # Skip if already exists
        if concept_ref in existing:
            continue

        # Find the target section
        target = sections_map.get(target_section)
        if not target:
            # Try first content section
            for s in ch.get("sections", []):
                if s["number"] not in ("Summary", "Points to Ponder"):
                    target = s
                    break

        if target:
            if "prerequisites" not in target:
                target["prerequisites"] = []
            target["prerequisites"].append({
                "type": "concept",
                "ref": concept_ref,
            })
            existing.add(concept_ref)
            added += 1

    print(f"✅ +{added} concepts")

    if not dry_run and added > 0:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return {"file": bn, "existing": len(existing) - added, "added": added, "status": "enriched"}


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        files = args
    else:
        files = sorted(
            f for f in glob.glob("data/ncert_*.json")
            if ".raw." not in f and ".progress." not in f
        )

    print(f"\n🔧 Ensuring min {MIN_CONCEPTS} concepts per chapter {'(DRY RUN)' if dry_run else ''}\n")

    results = []
    for fp in files:
        r = process_file(fp, dry_run)
        results.append(r)
        if r["status"] == "enriched":
            time.sleep(2)

    enriched = [r for r in results if r["status"] == "enriched"]
    total_added = sum(r["added"] for r in enriched)

    print(f"\n{'='*50}")
    print(f"✅ Enriched {len(enriched)} chapters, added {total_added} concepts total")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
