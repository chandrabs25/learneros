"""
Enrich existing JSON files with chapter summaries and section prerequisites.

This script reads existing extracted JSON files and uses Gemini (text-only, no vision)
to generate:
  1. Chapter summaries
  2. Section prerequisites (if missing)

Usage:
  uv run python extract/enrich_json.py data/ncert_physics_11_ch1.json
  uv run python extract/enrich_json.py data/ncert_physics_*.json

Environment:
  GEMINI_API_KEY=your_key_here
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import re

from dotenv import load_dotenv
from google import genai

load_dotenv()


def build_chapter_overview(data: dict) -> str:
    """Build a text overview of the chapter for the LLM."""
    ch = data.get("chapter") or {}
    sections = ch.get("sections") or []
    
    lines = []
    lines.append(f"Subject: {data.get('subject', 'unknown')}")
    lines.append(f"Grade: {data.get('grade', '?')}")
    lines.append(f"Chapter {ch.get('number', '?')}: {ch.get('title', 'Unknown')}")
    lines.append("")
    
    for s in sections:
        sn = s.get("number", "?")
        st = s.get("title", "")
        lines.append(f"\n## Section {sn}: {st}")
        
        for sub in (s.get("subsections") or []):
            title = sub.get("title", "")
            content = (sub.get("content_text") or "")[:500]  # First 500 chars
            lines.append(f"  ### {title}")
            if content:
                lines.append(f"    {content[:300]}...")
    
    return "\n".join(lines)


def build_section_list(data: dict) -> str:
    """Build a concise section list for prerequisite analysis."""
    ch = data.get("chapter") or {}
    subject = data.get("subject", "")
    grade = data.get("grade", "")
    ch_num = ch.get("number", "")
    sections = ch.get("sections") or []
    
    lines = []
    for s in sections:
        sn = s.get("number", "?")
        st = s.get("title", "")
        # List subsection titles
        sub_titles = [sub.get("title", "") for sub in (s.get("subsections") or [])]
        sub_str = ", ".join(sub_titles[:5])
        lines.append(f"Section {sn}: {st} (subsections: {sub_str})")
        
        # Show first subsection content briefly
        subs = s.get("subsections") or []
        if subs:
            content = (subs[0].get("content_text") or "")[:200]
            if content:
                lines.append(f"  Content preview: {content}...")
    
    return "\n".join(lines)


def call_gemini(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Call Gemini with text-only prompt. Returns raw text response."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
            else:
                print(f"  ⚠️ Empty response on attempt {attempt+1}")
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                wait = 30 * (attempt + 1)
                print(f"  ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ Error: {err}")
                if attempt < 2:
                    time.sleep(5)
    
    return ""


def generate_summary(data: dict) -> str:
    """Generate a chapter summary using Gemini."""
    overview = build_chapter_overview(data)
    ch = data.get("chapter") or {}
    
    prompt = f"""You are analyzing an NCERT textbook chapter. Generate a comprehensive chapter summary.

{overview}

Write a summary (150-250 words) that covers:
1. The main topics and concepts covered in this chapter
2. Key laws, principles, or formulas introduced
3. How the sections connect and build upon each other
4. The practical significance of the chapter content

Write in clear, educational language suitable for a student. Return ONLY the summary text, no headers or formatting."""

    return call_gemini(prompt)


def generate_prerequisites(data: dict) -> list[dict]:
    """Generate section prerequisites using Gemini. Returns list of {section_number, prerequisites}."""
    ch = data.get("chapter") or {}
    subject = data.get("subject", "physics")
    grade = data.get("grade", 11)
    ch_num = ch.get("number", 1)
    section_list = build_section_list(data)
    
    prompt = f"""You are analyzing section dependencies in an NCERT {subject} textbook (Grade {grade}, Chapter {ch_num}: {ch.get('title', '')}).

Here are the sections:

{section_list}

For each section, identify which OTHER sections from this chapter are prerequisites (a student needs to understand section X before learning section Y).

Return your answer as a JSON array. Each element should be:
{{
  "section": "<section_number>",
  "prerequisites": [
    {{"type": "section", "ref": "ncert:{subject}:{grade}:{ch_num}:<prereq_section_number>"}},
    {{"type": "concept", "ref": "concept:<concept_name>"}}
  ]
}}

Rules:
- Only include sections that TRULY depend on earlier sections (not every section needs prerequisites)
- The first section usually has no prerequisites from this chapter
- Use "concept" type for prerequisites from OTHER chapters (e.g., "concept:vectors", "concept:newtons_laws")
- Use "section" type for prerequisites within THIS chapter
- Keep concept names lowercase with underscores
- Return ONLY the JSON array, no explanation

Return valid JSON only."""

    response = call_gemini(prompt)
    
    # Parse JSON from response
    try:
        # Try to extract JSON array from the response
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        print(f"  ⚠️ Could not parse prerequisites JSON")
    
    return []


def enrich_file(filepath: str, force: bool = False) -> dict:
    """Enrich a single JSON file with summary and prerequisites."""
    print(f"\n{'='*60}")
    print(f"📖 Enriching: {os.path.basename(filepath)}")
    print(f"{'='*60}")
    
    with open(filepath) as f:
        data = json.load(f)
    
    ch = data.get("chapter") or {}
    changes = {}
    
    # 1. Generate chapter summary
    existing_summary = ch.get("summary")
    if not existing_summary or force:
        print("  🔄 Generating chapter summary...", end=" ", flush=True)
        summary = generate_summary(data)
        if summary:
            ch["summary"] = summary
            changes["summary"] = True
            print(f"✅ ({len(summary)} chars)")
        else:
            print("❌ Failed")
    else:
        print(f"  ✅ Summary already exists ({len(existing_summary)} chars)")
    
    # 2. Generate section prerequisites  
    sections = ch.get("sections") or []
    sections_needing_prereqs = [
        s for s in sections 
        if not s.get("prerequisites") 
        and str(s.get("number", "")).replace(".", "").replace(" ", "").isalnum()
        and str(s.get("number", "")).lower() not in ("summary", "points to ponder", "answers", "exercises")
    ]
    
    if sections_needing_prereqs or force:
        print(f"  🔄 Generating prerequisites for {len(sections_needing_prereqs)} sections...", end=" ", flush=True)
        prereq_data = generate_prerequisites(data)
        
        if prereq_data:
            # Apply prerequisites to sections
            prereq_map = {str(p.get("section")): p.get("prerequisites", []) for p in prereq_data}
            applied = 0
            for s in sections:
                sn = str(s.get("number", ""))
                if sn in prereq_map and (not s.get("prerequisites") or force):
                    s["prerequisites"] = prereq_map[sn]
                    applied += 1
            
            changes["prerequisites"] = applied
            print(f"✅ ({applied} sections updated)")
        else:
            print("❌ Failed")
    else:
        print(f"  ✅ Prerequisites already populated")
    
    # 3. Save
    if changes:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved with changes: {changes}")
    else:
        print(f"  ℹ️  No changes needed")
    
    return changes


def main():
    parser = argparse.ArgumentParser(description="Enrich JSON files with summaries and prerequisites")
    parser.add_argument("files", nargs="+", help="JSON files to enrich")
    parser.add_argument("--force", action="store_true", help="Overwrite existing enrichments")
    args = parser.parse_args()
    
    total_changes = {}
    for fp in args.files:
        if not os.path.exists(fp):
            print(f"  ❌ File not found: {fp}")
            continue
        if ".progress." in fp or ".raw." in fp:
            continue
        
        changes = enrich_file(fp, force=args.force)
        for k, v in changes.items():
            total_changes[k] = total_changes.get(k, 0) + (v if isinstance(v, int) else 1)
        
        # Rate limit between files
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"🎉 DONE! Total changes: {total_changes}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
