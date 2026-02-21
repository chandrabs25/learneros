"""
PDF → Common JSON Extraction Pipeline (Page-by-Page with Snapshots)

Strategy:
  1. Extract text from PDF one page at a time
  2. For each page, send it to Gemini with only a brief SNAPSHOT of prior context
     (last section title, last subsection order, any incomplete text)
  3. Each page returns a self-contained chunk of extracted content
  4. All page chunks are merged programmatically in Python
  5. Final merged JSON is validated against Pydantic models

Usage:
  uv run python -m extract.pdf_to_json \\
      --pdf path/to/chapter7.pdf \\
      --curriculum ncert --subject physics --grade 11 \\
      --chapter-number 7 \\
      --textbook-name "Physics Part I" \\
      --output data/gravity.json

Environment:
  GEMINI_API_KEY=your_key_here
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from db.models import TextbookChapter

load_dotenv()


# =============================================================================
# PDF Page Image Extraction (Vision-based)
# =============================================================================

PAGE_DPI = 200  # Good quality for text/math, 33% fewer tokens than 300 DPI


def extract_pages_from_pdf(pdf_path: str) -> list[bytes]:
    """Render each page of a chapter PDF as a 300 DPI PNG image.
    Returns a list of PNG byte strings."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=PAGE_DPI)
        pages.append(pix.tobytes("png"))
    doc.close()
    return pages


WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


def extract_chapter_title_from_pdf(pdf_path: str, subject: str = "", grade: int = 0, chapter_number: int = 0) -> str:
    """Extract chapter/unit title from the first page of an NCERT PDF.
    Tries PDF text parsing first, falls back to hardcoded NCERT title map.
    Returns empty string if no title found."""
    import fitz
    import re

    doc = fitz.open(pdf_path)
    text = doc[0].get_text()
    doc.close()

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for i, line in enumerate(lines):
        # Match "Chapter One/Two/..." or "Chapter 1/2/..." or "Unit 1/2/..."
        m = re.match(r'^(?:CHAPTER|Unit)\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            continue

        word = m.group(1).lower()
        ch_num = WORD_TO_NUM.get(word) or (int(word) if word.isdigit() else None)
        if ch_num is None:
            continue

        # Title is on the next line(s) until we hit a section number or junk
        title_parts = []
        for j in range(i + 1, min(i + 4, len(lines))):
            lj = lines[j]
            if re.match(r'^\d+\.\d+', lj):
                break
            if 'reprint' in lj.lower():
                continue
            if 'after studying' in lj.lower():
                break
            # Skip TOC-like lines (e.g. "Chapter 2 Human Reproduction")
            if re.match(r'^Chapter\s+\d+', lj, re.IGNORECASE):
                break
            if len(lj) > 2 and len(lj) < 80:
                title_parts.append(lj)

        if title_parts:
            title = " ".join(title_parts).strip().title()
            for w in [" And ", " Of ", " In ", " A ", " The ", " To ", " For "]:
                title = title.replace(w, w.lower())
            if title:
                title = title[0].upper() + title[1:]
            # Reject titles that are too long (likely paragraph text, not a title)
            if len(title) <= 80:
                return title

    # Fallback: hardcoded NCERT chapter titles
    key = (subject.lower(), grade, chapter_number)
    return NCERT_CHAPTER_TITLES.get(key, "")


# Authoritative NCERT chapter titles for all subjects
NCERT_CHAPTER_TITLES = {
    # Physics 11
    ("physics", 11, 1): "Units and Measurement",
    ("physics", 11, 2): "Motion in a Straight Line",
    ("physics", 11, 3): "Motion in a Plane",
    ("physics", 11, 4): "Laws of Motion",
    ("physics", 11, 5): "Work, Energy and Power",
    ("physics", 11, 6): "Systems of Particles and Rotational Motion",
    ("physics", 11, 7): "Gravitation",
    ("physics", 11, 8): "Mechanical Properties of Solids",
    ("physics", 11, 9): "Mechanical Properties of Fluids",
    ("physics", 11, 10): "Thermal Properties of Matter",
    ("physics", 11, 11): "Thermodynamics",
    ("physics", 11, 12): "Kinetic Theory",
    ("physics", 11, 13): "Oscillations",
    ("physics", 11, 14): "Waves",
    # Physics 12
    ("physics", 12, 1): "Electric Charges and Fields",
    ("physics", 12, 2): "Electrostatic Potential and Capacitance",
    ("physics", 12, 3): "Current Electricity",
    ("physics", 12, 4): "Moving Charges and Magnetism",
    ("physics", 12, 5): "Magnetism and Matter",
    ("physics", 12, 6): "Electromagnetic Induction",
    ("physics", 12, 7): "Alternating Current",
    ("physics", 12, 8): "Electromagnetic Waves",
    ("physics", 12, 9): "Ray Optics and Optical Instruments",
    ("physics", 12, 10): "Wave Optics",
    ("physics", 12, 11): "Dual Nature of Radiation and Matter",
    ("physics", 12, 12): "Atoms",
    ("physics", 12, 13): "Nuclei",
    ("physics", 12, 14): "Semiconductor Electronics: Materials, Devices and Simple Circuits",
    # Chemistry 11
    ("chemistry", 11, 1): "Some Basic Concepts of Chemistry",
    ("chemistry", 11, 2): "Structure of Atom",
    ("chemistry", 11, 3): "Classification of Elements and Periodicity in Properties",
    ("chemistry", 11, 4): "Chemical Bonding and Molecular Structure",
    ("chemistry", 11, 5): "Thermodynamics",
    ("chemistry", 11, 6): "Equilibrium",
    ("chemistry", 11, 7): "Redox Reactions",
    ("chemistry", 11, 8): "Organic Chemistry: Some Basic Principles and Techniques",
    ("chemistry", 11, 9): "Hydrocarbons",
    # Chemistry 12
    ("chemistry", 12, 1): "Solutions",
    ("chemistry", 12, 2): "Electrochemistry",
    ("chemistry", 12, 3): "Chemical Kinetics",
    ("chemistry", 12, 4): "The d- and f-Block Elements",
    ("chemistry", 12, 5): "Coordination Compounds",
    ("chemistry", 12, 6): "Haloalkanes and Haloarenes",
    ("chemistry", 12, 7): "Alcohols, Phenols and Ethers",
    ("chemistry", 12, 8): "Aldehydes, Ketones and Carboxylic Acids",
    ("chemistry", 12, 9): "Amines",
    ("chemistry", 12, 10): "Biomolecules",
    # Biology 11
    ("biology", 11, 1): "The Living World",
    ("biology", 11, 2): "Biological Classification",
    ("biology", 11, 3): "Plant Kingdom",
    ("biology", 11, 4): "Animal Kingdom",
    ("biology", 11, 5): "Morphology of Flowering Plants",
    ("biology", 11, 6): "Anatomy of Flowering Plants",
    ("biology", 11, 7): "Structural Organisation in Animals",
    ("biology", 11, 8): "Cell: The Unit of Life",
    ("biology", 11, 9): "Biomolecules",
    ("biology", 11, 10): "Cell Cycle and Cell Division",
    ("biology", 11, 11): "Photosynthesis in Higher Plants",
    ("biology", 11, 12): "Respiration in Plants",
    ("biology", 11, 13): "Plant Growth and Development",
    ("biology", 11, 14): "Breathing and Exchange of Gases",
    ("biology", 11, 15): "Body Fluids and Circulation",
    ("biology", 11, 16): "Excretory Products and Their Elimination",
    ("biology", 11, 17): "Locomotion and Movement",
    ("biology", 11, 18): "Neural Control and Coordination",
    ("biology", 11, 19): "Chemical Coordination and Integration",
    # Biology 12
    ("biology", 12, 1): "Sexual Reproduction in Flowering Plants",
    ("biology", 12, 2): "Human Reproduction",
    ("biology", 12, 3): "Reproductive Health",
    ("biology", 12, 4): "Principles of Inheritance and Variation",
    ("biology", 12, 5): "Molecular Basis of Inheritance",
    ("biology", 12, 6): "Evolution",
    ("biology", 12, 7): "Human Health and Disease",
    ("biology", 12, 8): "Microbes in Human Welfare",
    ("biology", 12, 9): "Biotechnology: Principles and Processes",
    ("biology", 12, 10): "Biotechnology and Its Applications",
    ("biology", 12, 11): "Organisms and Populations",
    ("biology", 12, 12): "Ecosystem",
    ("biology", 12, 13): "Biodiversity and Conservation",
}


# =============================================================================
# Snapshot — lightweight context from prior pages
# =============================================================================


def build_snapshot(chunks: list[dict]) -> str:
    """
    Build a brief text snapshot from previously extracted chunks.
    Only includes the minimal info the LLM needs for continuity:
      - Which section/subsection we were last in
      - Any trailing incomplete text
      - Warnings about skipped pages
    """
    if not chunks:
        return "No prior content. This is the first page of the chapter."

    snapshot_lines = []
    last = chunks[-1]

    # Collect what sections have been seen
    all_sections = []
    for c in chunks:
        for sec in c.get("sections", []):
            all_sections.append(sec["number"] + ": " + sec["title"])

    if all_sections:
        snapshot_lines.append(f"Sections extracted so far: {', '.join(all_sections)}")

    # Check if any chunks had skipped pages
    skipped_pages = []
    for c in chunks:
        for sec in c.get("sections", []):
            for sub in sec.get("subsections", []):
                if sub.get("_skipped"):
                    skipped_pages.append(sub.get("_skipped_pages", "?"))
    if skipped_pages:
        snapshot_lines.append(f"⚠ PAGES SKIPPED (could not be extracted): {', '.join(skipped_pages)}. These pages may contain additional sections not listed above. Use the section numbers visible on YOUR pages, not sequential from the list above.")

    # Last section info
    last_sections = last.get("sections", [])
    if last_sections:
        last_sec = last_sections[-1]
        snapshot_lines.append(f"Last section: {last_sec['number']} — {last_sec['title']}")

        last_subs = last_sec.get("subsections", [])
        if last_subs:
            last_sub = last_subs[-1]
            snapshot_lines.append(
                f"Last subsection: order {last_sub.get('order', '?')}, "
                f"title \"{last_sub.get('title', '(untitled)')}\""
            )
            # Check for incomplete text
            if last_sub.get("content_text", "").endswith("[CONTINUES]"):
                # Send the last ~200 chars so LLM can continue naturally
                trailing = last_sub["content_text"][-200:]
                snapshot_lines.append(f"⚠ INCOMPLETE — trailing text: \"...{trailing}\"")

    # Last exercise info
    last_exercises = last.get("exercises", {}).get("items", [])
    if last_exercises:
        last_ex = last_exercises[-1]
        snapshot_lines.append(f"Last exercise extracted: #{last_ex['number']}")
        if last_ex.get("problem", "").endswith("[CONTINUES]"):
            trailing = last_ex["problem"][-200:]
            snapshot_lines.append(f"⚠ INCOMPLETE exercise — trailing text: \"...{trailing}\"")

    return "\n".join(snapshot_lines) if snapshot_lines else "No prior content."


# =============================================================================
# LLM Prompt
# =============================================================================


def build_page_prompt(
    page_start: int,
    page_end: int,
    total_pages: int,
    snapshot: str,
    curriculum: str,
    subject: str,
    grade: int,
    chapter_number: int,
    textbook_name: str,
) -> str:
    """Build the extraction prompt for a batch of page images."""
    page_range = f"pages {page_start}-{page_end}" if page_start != page_end else f"page {page_start}"

    return f"""You are an expert educational content analyst building structured teaching materials for an AI tutoring system. You are analyzing {page_range} of {total_pages} from a {curriculum.upper()} {subject.title()} Class {grade} textbook, Chapter {chapter_number} ("{textbook_name}").

## Context from Previous Pages
{snapshot}

## Your Task
Analyze the attached page images and create detailed, comprehensive structured notes capturing ALL concepts, explanations, derivations, laws, definitions, examples, and exercises visible on these pages. Structure the content into the JSON format below. Do NOT include content from earlier pages — only analyze what is visible on the attached images.

## Output JSON Structure
Return a JSON object with this structure:
{{
  "sections": [
    {{
      "number": "7.3",
      "title": "Section Title",
      "subsections": [
        {{
          "order": 1,
          "title": "Subsection Title",
          "content_text": "Detailed notes covering the concepts...",
          "content_type": "explanation",
          "worked_examples": [
            {{"label": "Example 7.1", "problem": "...", "solution": "..."}}
          ],
          "diagrams": [
            {{"label": "Fig 7.1", "description": "..."}}
          ],
          "tables": [
            {{"label": "Table 1.1", "caption": "Physical Constants", "headers": ["Constant", "Symbol", "Value"], "rows": [["Speed of light", "c", "$3 \\times 10^8$ m/s"]]}}
          ]
        }}
      ],
      "prerequisites": [
        {{"type": "concept", "ref": "concept:vectors"}},
        {{"type": "section", "ref": "{curriculum}:{subject}:{grade}:6:2"}}
      ]
    }}
  ],
  "exercises": {{
    "title": "Exercises",
    "items": [
      {{
        "number": 1,
        "problem": "...",
        "solution": "...",
        "difficulty": "easy",
        "exercise_type": "numerical",
        "tests_concepts": ["concept:gravity"]
      }}
    ]
  }}
}}

## Rules

### Sections & Subsections
- If these pages CONTINUE a section from the previous batch, use the SAME section number.
- If a new numbered section starts on these pages, add it as a separate entry.
- Split content into subsections (atomic teaching units, 1-4 paragraphs each):
  - Each concept, law, formula, derivation step = separate subsection
  - Each worked example's explanation = separate subsection
- `content_text` must be thorough and detailed — capture every concept, equation, explanation, and nuance from the pages. A student should be able to learn the topic fully from your notes alone. Do NOT skip or oversimplify.
- `content_type`: "explanation", "derivation", "law", "definition", "theorem", "experiment", or "application"
- Content that spans across pages within this batch should be combined into a single subsection. Do NOT split just because of a page boundary.
- **SKIP** any "Objectives", "Learning Outcomes", or "After studying this unit you will be able to" bullet lists — these are NOT content to extract.
- **SKIP** page headers, footers, page numbers, QR codes, and "Reprint 2025-26" annotations.
- For multi-column layouts, read the LEFT column first, then the RIGHT column, in natural reading order.

### Continuity
- If the previous batch had incomplete content (marked in the snapshot), the beginning of this batch likely continues it. Start the first subsection with that continued text.
- If content at the END of this batch is cut off, end `content_text` with " [CONTINUES]"
- Continue subsection `order` numbering from where the previous batch left off for the same section. If snapshot says last subsection was order 4, the next one should be order 5.

### Worked Examples
- Label: "Example 7.1", Problem & Solution separated
- Use LaTeX for math: $F = G\\frac{{m_1 m_2}}{{r^2}}$, $\\vec{{F}}$, $\\frac{{a}}{{b}}$

### Diagrams
- When you see a figure/diagram in the page images, add a diagram entry
- Set `description` to a detailed description of what the figure depicts. Leave `image_url` as null.

### Tables
- When the pages contain a table (data in rows/columns, comparison charts, lists of constants, etc.), extract it as a structured table.
- `label`: The table label if present (e.g. "Table 1.1"), or null if unlabeled.
- `caption`: A short title/caption for the table.
- `headers`: List of column header strings.
- `rows`: List of rows, each row is a list of cell strings. Use LaTeX for any math in cells.
- Also reference the table naturally in `content_text` (e.g. "The following table shows...").

### Exercises
- Only include if these pages have end-of-chapter exercises
- Number, problem text, solution (if available), difficulty, type

### Prerequisites
- Only include for NEW sections starting on these pages

### Math Formatting
- ALL math in LaTeX: inline $...$, display $$...$$

## Output
Return ONLY valid JSON matching the structure above. No markdown fences, no explanation."""


# =============================================================================
# Page Chunk Schema (for structured output)
# =============================================================================


PAGE_CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chapter_title": {
            "type": "string",
            "description": "The actual chapter/unit name as shown on the page header or title page (e.g. 'Electric Charges and Fields', 'Thermodynamics'). Not the section title. Leave empty string if not visible on these pages.",
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "string"},
                    "title": {"type": "string"},
                    "subsections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "order": {"type": "integer"},
                                "title": {"type": "string"},
                                "content_text": {"type": "string"},
                                "content_type": {
                                    "type": "string",
                                    "enum": ["explanation", "derivation", "law",
                                             "definition", "theorem", "experiment",
                                             "application"],
                                },
                                "worked_examples": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "problem": {"type": "string"},
                                            "solution": {"type": "string"},
                                        },
                                        "required": ["label", "problem", "solution"],
                                    },
                                },
                                "diagrams": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                        "required": ["label", "description"],
                                    },
                                },
                                "tables": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "caption": {"type": "string"},
                                            "headers": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                            "rows": {
                                                "type": "array",
                                                "items": {
                                                    "type": "array",
                                                    "items": {"type": "string"},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                            "required": ["order", "title", "content_text", "content_type"],
                        },
                    },
                    "prerequisites": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["section", "concept"]},
                                "ref": {"type": "string"},
                            },
                            "required": ["type", "ref"],
                        },
                    },
                },
                "required": ["number", "title"],
            },
        },
        "exercises": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer"},
                            "problem": {"type": "string"},
                            "solution": {"type": "string"},
                            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                            "exercise_type": {
                                "type": "string",
                                "enum": ["conceptual", "numerical", "derivation",
                                         "mcq", "short_answer", "long_answer"],
                            },
                            "tests_concepts": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["number", "problem"],
                    },
                },
            },
        },
    },
}


# =============================================================================
# LLM Call
# =============================================================================


import time
import re


def _repair_json(text: str) -> dict | None:
    """
    Attempt to repair truncated JSON from the LLM.
    Handles unterminated strings and missing closing brackets/braces.
    Returns parsed dict on success, None on failure.
    """
    s = text.rstrip()

    # Close any unterminated string literal
    # Count unescaped quotes — if odd, add a closing quote
    in_string = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\\' and in_string:
            i += 2  # skip escaped char
            continue
        if ch == '"':
            in_string = not in_string
        i += 1
    if in_string:
        s += '"'

    # Remove any trailing comma before we close brackets
    s = re.sub(r',\s*$', '', s)

    # Close any open brackets/braces
    stack = []
    in_str = False
    j = 0
    while j < len(s):
        ch = s[j]
        if ch == '\\' and in_str:
            j += 2
            continue
        if ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch in '{[':
                stack.append('}' if ch == '{' else ']')
            elif ch in '}]' and stack:
                stack.pop()
        j += 1

    # Append missing closers
    s += ''.join(reversed(stack))

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


class RecitationError(Exception):
    """Raised when Gemini blocks a response due to RECITATION (copyrighted content)."""
    pass


def call_gemini(
    prompt: str,
    page_images: list[bytes] | None = None,
    model: str = "gemini-3-flash-preview",
    max_retries: int = 5,
) -> dict:
    """
    Send page images + prompt to Gemini and get structured JSON back.
    Uses multimodal input: text prompt + PNG page images.
    Retries with exponential backoff on transient errors.
    """
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")

    client = genai.Client(api_key=api_key)
    backoff_times = [10, 30, 60, 120, 240]  # seconds

    # Build multimodal content: prompt text + page images
    contents = [prompt]
    if page_images:
        for img_bytes in page_images:
            contents.append(
                types.Part.from_bytes(data=img_bytes, mime_type="image/png")
            )

    consecutive_recitation = 0
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": PAGE_CHUNK_SCHEMA,
                    "temperature": 0.1,
                },
            )
            # Handle empty response — log why
            if response.text is None:
                details = []
                is_recitation = False
                if hasattr(response, 'candidates') and response.candidates:
                    c = response.candidates[0]
                    finish = getattr(c, 'finish_reason', None)
                    details.append(f"finish_reason={finish}")
                    if finish and 'RECITATION' in str(finish):
                        is_recitation = True
                    if hasattr(c, 'safety_ratings') and c.safety_ratings:
                        for r in c.safety_ratings:
                            details.append(f"{r.category}={r.probability}")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    details.append(f"prompt_feedback={response.prompt_feedback}")
                detail_str = ", ".join(details) if details else "no details available"

                if is_recitation:
                    consecutive_recitation += 1
                    if consecutive_recitation >= 1:
                        raise RecitationError(f"RECITATION block — content flagged as copyrighted")
                else:
                    consecutive_recitation = 0

                raise ValueError(f"Gemini returned empty response ({detail_str})")

            consecutive_recitation = 0  # reset on success
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                # Try to repair truncated JSON
                repaired = _repair_json(response.text)
                if repaired is not None:
                    print("🔧 (repaired truncated JSON)", end=" ", flush=True)
                    return repaired
                # Treat as retryable
                raise
        except RecitationError:
            raise  # Don't retry — propagate immediately
        except Exception as e:
            error_str = str(e)
            is_retryable = (
                "503" in error_str
                or "429" in error_str
                or "UNAVAILABLE" in error_str
                or "RESOURCE_EXHAUSTED" in error_str
                or isinstance(e, json.JSONDecodeError)
                or isinstance(e, ValueError)
            )

            if is_retryable and attempt < max_retries:
                wait = backoff_times[min(attempt, len(backoff_times) - 1)]
                reason = "Malformed JSON" if isinstance(e, json.JSONDecodeError) else "API error"
                print(f"\n   ⏳ {reason}: {error_str[:300]}")
                print(f"      Retrying in {wait}s (attempt {attempt + 1}/{max_retries})...", end=" ", flush=True)
                time.sleep(wait)
                continue
            raise


# =============================================================================
# Programmatic Merging
# =============================================================================


def _titles_match(title_a: str, title_b: str) -> bool:
    """
    Check if two subsection titles are similar enough to indicate
    they're actually the same subsection split across pages.
    """
    a = title_a.strip().lower()
    b = title_b.strip().lower()

    # Exact match
    if a == b:
        return True

    # One contains the other (handles "X" vs "X (continued)" etc.)
    if a in b or b in a:
        return True

    # Strip common suffixes the LLM might add
    for suffix in [" (continued)", " (contd)", " continued", " contd", " cont"]:
        a_clean = a.removesuffix(suffix)
        b_clean = b.removesuffix(suffix)
        if a_clean == b_clean:
            return True

    return False


def _normalize_concept_ref(ref: str) -> str:
    """
    Normalize a concept reference to 'concept:snake_case' format.
    Examples:
        'vectors'              -> 'concept:vectors'
        'concept:vectors'      -> 'concept:vectors'
        'Coulomb's Law'        -> 'concept:coulombs_law'
        'inverse square law'   -> 'concept:inverse_square_law'
        'Vector Area'          -> 'concept:vector_area'
    """
    s = ref.strip()
    # Strip existing concept: prefix
    if s.lower().startswith("concept:"):
        s = s[len("concept:"):]
    # Lowercase
    s = s.lower()
    # Strip apostrophes before general cleanup (so "coulomb's" -> "coulombs" not "coulomb_s")
    s = s.replace("'", "").replace("\u2019", "")
    # Replace special chars with underscores
    s = re.sub(r"[^a-z0-9]+", "_", s)
    # Strip leading/trailing underscores
    s = s.strip("_")
    return f"concept:{s}"


def merge_chunks(
    chunks: list[dict],
    curriculum: str,
    subject: str,
    grade: int,
    chapter_number: int,
    textbook_name: str,
    chapter_title: str,
) -> dict:
    """
    Merge all page chunks into the final TextbookChapter JSON.
    Handles:
      - Combining subsections for the same section across pages
      - Stitching [CONTINUES] text across page boundaries
      - Collecting all exercises into a single ExerciseSet
    """
    merged_sections: dict[str, dict] = {}  # keyed by section number
    all_exercises: list[dict] = []
    exercise_title = "Exercises"

    for chunk in chunks:
        # Merge sections
        for sec in chunk.get("sections", []):
            sec_num = sec["number"]

            if sec_num not in merged_sections:
                # New section
                merged_sections[sec_num] = {
                    "number": sec_num,
                    "title": sec["title"],
                    "subsections": [],
                    "prerequisites": sec.get("prerequisites", []),
                }

            existing = merged_sections[sec_num]

            # Merge subsections
            new_subs = sec.get("subsections", [])
            if existing["subsections"] and new_subs:
                last_existing = existing["subsections"][-1]
                first_new = new_subs[0]

                # Stitch [CONTINUES] text
                if last_existing.get("content_text", "").endswith("[CONTINUES]"):
                    last_existing["content_text"] = (
                        last_existing["content_text"][:-len("[CONTINUES]")].rstrip()
                        + " " + first_new.get("content_text", "")
                    )
                    # Merge worked examples, diagrams, and tables from the continued chunk
                    last_existing.setdefault("worked_examples", []).extend(
                        first_new.get("worked_examples", [])
                    )
                    last_existing.setdefault("diagrams", []).extend(
                        first_new.get("diagrams", [])
                    )
                    last_existing.setdefault("tables", []).extend(
                        first_new.get("tables", [])
                    )
                    new_subs = new_subs[1:]  # Skip first since it was merged

            existing["subsections"].extend(new_subs)

            # Merge prerequisites (deduplicate, skip malformed)
            existing_prereq_refs = {p.get("ref") for p in existing.get("prerequisites", []) if p.get("ref")}
            for prereq in sec.get("prerequisites", []):
                if not prereq.get("ref") or not prereq.get("type"):
                    continue  # Skip malformed prereqs
                if prereq["ref"] not in existing_prereq_refs:
                    existing["prerequisites"].append(prereq)
                    existing_prereq_refs.add(prereq["ref"])

        # Collect exercises
        ex = chunk.get("exercises")
        if ex:
            exercise_title = ex.get("title", exercise_title)
            for item in ex.get("items", []):
                all_exercises.append(item)

    # Stitch [CONTINUES] in exercises
    for i in range(len(all_exercises) - 1):
        if all_exercises[i].get("problem", "").endswith("[CONTINUES]"):
            all_exercises[i]["problem"] = (
                all_exercises[i]["problem"][:-len("[CONTINUES]")].rstrip()
                + " " + all_exercises[i + 1].get("problem", "")
            )
            all_exercises[i + 1]["problem"] = ""  # Will clean up

    all_exercises = [e for e in all_exercises if e.get("problem")]

    # ---- Post-merge: combine consecutive same-titled subsections ----
    # The LLM often splits a single subsection across page boundaries into
    # two chunks with the same (or near-identical) title. Merge those.
    for sec in merged_sections.values():
        if len(sec["subsections"]) < 2:
            continue

        merged_subs = [sec["subsections"][0]]
        for sub in sec["subsections"][1:]:
            prev = merged_subs[-1]

            # Detect same-title or [CONTINUES] marker
            same_title = _titles_match(prev.get("title", ""), sub.get("title", ""))
            continues = prev.get("content_text", "").rstrip().endswith("[CONTINUES]")

            if same_title or continues:
                # Stitch content text
                prev_text = prev.get("content_text", "")
                if prev_text.rstrip().endswith("[CONTINUES]"):
                    prev_text = prev_text.rstrip()[:-len("[CONTINUES]")].rstrip()
                prev["content_text"] = prev_text + "\n" + sub.get("content_text", "")

                # Merge worked examples, diagrams, & tables
                prev.setdefault("worked_examples", []).extend(
                    sub.get("worked_examples", [])
                )
                prev.setdefault("diagrams", []).extend(
                    sub.get("diagrams", [])
                )
                prev.setdefault("tables", []).extend(
                    sub.get("tables", [])
                )
            else:
                merged_subs.append(sub)

        sec["subsections"] = merged_subs

    # Re-number subsection orders sequentially within each section
    for sec in merged_sections.values():
        for idx, sub in enumerate(sec["subsections"], 1):
            sub["order"] = idx

    # Deduplicate exercises by number
    seen_ex = set()
    deduped_exercises = []
    for ex in all_exercises:
        if ex["number"] not in seen_ex:
            seen_ex.add(ex["number"])
            deduped_exercises.append(ex)

    # ---- Fix empty content_type values ----
    valid_content_types = {"explanation", "derivation", "law", "definition", "theorem", "experiment", "application"}
    for sec in merged_sections.values():
        for sub in sec.get("subsections", []):
            if sub.get("content_type", "") not in valid_content_types:
                sub["content_type"] = "explanation"

    # ---- Fix empty exercise_type values ----
    valid_exercise_types = {"conceptual", "numerical", "derivation", "mcq", "short_answer", "long_answer"}
    for ex in deduped_exercises:
        if ex.get("exercise_type", "") not in valid_exercise_types:
            ex["exercise_type"] = "conceptual"

    # ---- Normalize all references ----
    id_prefix = f"{curriculum}:{subject}:{grade}:{chapter_number}"

    for sec in merged_sections.values():
        normalized_prereqs = []
        seen_refs = set()
        for prereq in sec.get("prerequisites", []):
            if not prereq.get("type") or not prereq.get("ref"):
                continue  # Skip malformed prereqs
            if prereq["type"] == "concept":
                prereq["ref"] = _normalize_concept_ref(prereq["ref"])
            elif prereq["type"] == "section":
                ref = prereq["ref"].strip()
                # Case 1: Bare section number (e.g. "1.1", "1.10.1")
                if re.match(r"^[\d.]+$", ref) or ref.upper() == "SUMMARY":
                    ref = f"{id_prefix}:{ref}"
                # Case 2: Full format but with extra colons in section part
                # e.g. "ncert:physics:11:1:7:1" → "ncert:physics:11:1:7.1"
                elif ref.startswith(id_prefix + ":"):
                    suffix = ref[len(id_prefix) + 1:]  # "7:1"
                    # If suffix has colons (more than one part), convert to dots
                    if ":" in suffix:
                        suffix = suffix.replace(":", ".")
                    ref = f"{id_prefix}:{suffix}"
                prereq["ref"] = ref
            # Deduplicate after normalization
            if prereq["ref"] not in seen_refs:
                seen_refs.add(prereq["ref"])
                normalized_prereqs.append(prereq)
        sec["prerequisites"] = normalized_prereqs

    for ex in deduped_exercises:
        ex["tests_concepts"] = [
            _normalize_concept_ref(tc) for tc in ex.get("tests_concepts", [])
        ]

    # Derive chapter title from first section if not clear
    if not chapter_title and merged_sections:
        first_sec = list(merged_sections.values())[0]
        chapter_title = first_sec["title"]

    # Build final structure
    final = {
        "curriculum": curriculum,
        "subject": subject,
        "grade": grade,
        "textbook_name": textbook_name,
        "volume": 1,
        "chapter": {
            "number": chapter_number,
            "title": chapter_title,
            "summary": None,
            "sections": list(merged_sections.values()),
            "exercises": {
                "title": exercise_title,
                "items": deduped_exercises,
            } if deduped_exercises else None,
        },
    }

    return final


# =============================================================================
# Main Pipeline
# =============================================================================


def extract_chapter(
    pdf_path: str,
    curriculum: str,
    subject: str,
    grade: int,
    chapter_number: int,
    textbook_name: str,
    output_path: str,
    model: str = "gemini-3-flash-preview",
    resume: bool = False,
) -> TextbookChapter:
    """Full pipeline: PDF → page-by-page chunks → merge → validate → save."""

    # Step 1: Extract all pages
    print(f"\n📄 Extracting pages from {pdf_path}...")
    pages = extract_pages_from_pdf(pdf_path)
    print(f"   Found {len(pages)} pages\n")

    if not pages:
        raise ValueError("No pages found in PDF.")

    chunks: list[dict] = []
    chapter_title = extract_chapter_title_from_pdf(pdf_path, subject=subject, grade=grade, chapter_number=chapter_number)
    if chapter_title:
        print(f"   📖 Chapter title: \"{chapter_title}\"\n")
    batch_size = 3  # pages per LLM call
    batches_to_skip = 0

    # Resume from progress file if requested
    progress_path = output_path.replace(".json", ".progress.json")
    if resume and os.path.exists(progress_path):
        with open(progress_path) as f:
            chunks = json.load(f)
        batches_to_skip = len(chunks)
        for c in chunks:
            ct = c.get("chapter_title", "").strip()
            if ct and ct.lower() not in ("introduction", ""):
                chapter_title = ct
                break
        print(f"   ♻️  Resuming: loaded {batches_to_skip} batches from progress file\n")

    # Step 2: Process pages in batches of 3 images
    i = 0
    while i < len(pages):
        # Collect batch of page images
        batch_images = []
        batch_indices = []
        while i < len(pages) and len(batch_images) < batch_size:
            i += 1
            batch_images.append(pages[i - 1])
            batch_indices.append(i)  # 1-indexed page number

        if not batch_images:
            continue

        # Skip batches we already have from a previous run
        if batches_to_skip > 0:
            page_start = batch_indices[0]
            page_end = batch_indices[-1]
            page_label = f"Pages {page_start}-{page_end}" if page_start != page_end else f"Page {page_start}"
            print(f"   {page_label}/{len(pages)}: ⏩ skipped (already in progress file)")
            batches_to_skip -= 1
            continue

        page_start = batch_indices[0]
        page_end = batch_indices[-1]
        total_kb = sum(len(img) for img in batch_images) // 1024

        snapshot = build_snapshot(chunks)

        # Pick up chapter title from earlier chunks if not yet found
        if not chapter_title:
            for c in chunks:
                ct = c.get("chapter_title", "").strip()
                if ct and ct.lower() not in ("introduction", ""):
                    chapter_title = ct
                    break

        prompt = build_page_prompt(
            page_start=page_start,
            page_end=page_end,
            total_pages=len(pages),
            snapshot=snapshot,
            curriculum=curriculum,
            subject=subject,
            grade=grade,
            chapter_number=chapter_number,
            textbook_name=textbook_name,
        )

        page_label = f"Pages {page_start}-{page_end}" if page_start != page_end else f"Page {page_start}"
        print(f"   {page_label}/{len(pages)}: 🤖 extracting ({total_kb} KB images)...", end=" ", flush=True)

        try:
            chunk = call_gemini(prompt, page_images=batch_images, model=model)
            chunks.append(chunk)

            # Track chapter title
            ct = chunk.get("chapter_title", "").strip()
            if ct and ct.lower() not in ("introduction", "") and not chapter_title:
                chapter_title = ct

            n_secs = len(chunk.get("sections", []))
            n_subs = sum(len(s.get("subsections", [])) for s in chunk.get("sections", []))
            n_ex = len(chunk.get("exercises", {}).get("items", []))
            print(f"✅ ({n_secs} sections, {n_subs} subsections, {n_ex} exercises)")
        except RecitationError:
            # Stage 1: Retry with a summarize prompt (less likely to trigger RECITATION)
            print(f"\n   🔄 RECITATION — retrying with summarize prompt...", end=" ", flush=True)
            summarize_prompt = prompt.replace(
                "must be thorough and detailed — capture every concept, equation, explanation, and nuance from the pages. A student should be able to learn the topic fully from your notes alone. Do NOT skip or oversimplify.",
                "should SUMMARIZE each paragraph in your own words while preserving all key concepts, equations, laws, and definitions. Rephrase the content — do NOT reproduce it verbatim. Maintain the same structure (sections, subsections) but express ideas in your own language."
            )
            try:
                chunk = call_gemini(summarize_prompt, page_images=batch_images, model=model)
                chunks.append(chunk)

                ct = chunk.get("chapter_title", "").strip()
                if ct and ct.lower() not in ("introduction", "") and not chapter_title:
                    chapter_title = ct

                n_secs = len(chunk.get("sections", []))
                n_subs = sum(len(s.get("subsections", [])) for s in chunk.get("sections", []))
                n_ex = len(chunk.get("exercises", {}).get("items", []))
                print(f"✅ summarized ({n_secs} sections, {n_subs} subsections, {n_ex} exercises)")
            except RecitationError:
                # Stage 2: Skip entirely
                print(f"⚠️  SKIPPED (RECITATION block — pages {page_start}-{page_end})")
                skip_log = os.path.join(os.path.dirname(output_path) or ".", "recitation_skipped.md")
                pdf_basename = os.path.basename(pdf_path)
                with open(skip_log, "a") as f:
                    f.write(f"- **{curriculum} {subject} {grade} ch{chapter_number}** — `{pdf_basename}` pages {page_start}-{page_end}/{len(pages)}\n")
                print(f"   📝 Logged to {skip_log}")

                # Insert a placeholder chunk using the PREVIOUS chunk's structure
                # so the NEXT batch gets correct continuity context
                placeholder_sections = []
                if chunks:
                    last_chunk = chunks[-1]
                    last_secs = last_chunk.get("sections", [])
                    if last_secs:
                        last_sec = last_secs[-1]
                        last_order = max((s.get("order", 0) for s in last_sec.get("subsections", [])), default=0)
                        placeholder_sections.append({
                            "number": last_sec["number"],
                            "title": last_sec["title"],
                            "subsections": [{
                                "order": last_order + 1,
                                "title": f"[SKIPPED — pages {page_start}-{page_end} blocked by RECITATION]",
                                "content_text": f"[SKIPPED — this content needs manual extraction from pages {page_start}-{page_end}] [CONTINUES]",
                                "content_type": "explanation",
                                "_skipped": True,
                                "_skipped_pages": f"{page_start}-{page_end}",
                                "_skipped_pdf": os.path.basename(pdf_path),
                            }]
                        })

                if not placeholder_sections:
                    placeholder_sections.append({
                        "number": "?",
                        "title": f"[SKIPPED pages {page_start}-{page_end}]",
                        "subsections": [{
                            "order": 1,
                            "title": f"[SKIPPED — pages {page_start}-{page_end} blocked by RECITATION]",
                            "content_text": f"[SKIPPED — this content needs manual extraction from pages {page_start}-{page_end}] [CONTINUES]",
                            "content_type": "explanation",
                            "_skipped": True,
                            "_skipped_pages": f"{page_start}-{page_end}",
                            "_skipped_pdf": os.path.basename(pdf_path),
                        }]
                    })

                chunks.append({"sections": placeholder_sections, "exercises": {"title": "Exercises", "items": []}})
            continue  # proceed to next batch
        except Exception as e:
            print(f"❌ Error: {e}")
            if chunks:
                progress_path = output_path.replace(".json", ".progress.json")
                os.makedirs(os.path.dirname(progress_path) or ".", exist_ok=True)
                with open(progress_path, "w") as f:
                    json.dump(chunks, f, indent=2, ensure_ascii=False)
                print(f"   💾 Page chunks saved to: {progress_path}")
            raise

    if not chunks:
        raise ValueError("No content extracted from any page.")

    # Save progress after successful extraction (before merge)
    # This ensures retries on validation errors don't re-extract
    progress_path = output_path.replace(".json", ".progress.json")
    os.makedirs(os.path.dirname(progress_path) or ".", exist_ok=True)
    with open(progress_path, "w") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    # Step 3: Merge all chunks
    print(f"\n🔗 Merging {len(chunks)} page chunks...")
    merged = merge_chunks(
        chunks=chunks,
        curriculum=curriculum,
        subject=subject,
        grade=grade,
        chapter_number=chapter_number,
        textbook_name=textbook_name,
        chapter_title=chapter_title,
    )

    # Step 4: Sanitize before validation
    valid_difficulties = {"easy", "medium", "hard"}
    for item in ((merged.get("chapter") or {}).get("exercises") or {}).get("items") or []:
        if item.get("difficulty", "") not in valid_difficulties:
            item["difficulty"] = "medium"

    # Step 5: Validate with Pydantic
    print("✅ Validating against Pydantic schema...")
    try:
        chapter_data = TextbookChapter(**merged)
    except ValidationError as e:
        debug_path = output_path.replace(".json", ".raw.json")
        os.makedirs(os.path.dirname(debug_path) or ".", exist_ok=True)
        with open(debug_path, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"❌ Validation failed! Raw output saved to: {debug_path}")
        print(f"   Errors: {e.error_count()}")
        for err in e.errors():
            print(f"   - {' → '.join(str(x) for x in err['loc'])}: {err['msg']}")
        raise

    # Step 5: Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(chapter_data.model_dump(), f, indent=2, ensure_ascii=False)

    # Clean up progress file on success
    if os.path.exists(progress_path):
        os.remove(progress_path)

    # Summary
    total_subsections = sum(len(s.subsections) for s in chapter_data.chapter.sections)
    total_examples = sum(
        len(ss.worked_examples)
        for s in chapter_data.chapter.sections
        for ss in s.subsections
    )
    total_exercises = (
        len(chapter_data.chapter.exercises.items)
        if chapter_data.chapter.exercises
        else 0
    )

    print(f"\n🎉 Chapter {chapter_data.chapter.number}: {chapter_data.chapter.title}")
    print(f"   Sections:     {len(chapter_data.chapter.sections)}")
    print(f"   Subsections:  {total_subsections}")
    print(f"   Examples:     {total_examples}")
    print(f"   Exercises:    {total_exercises}")
    print(f"   Saved to:     {output_path}\n")

    return chapter_data


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Extract a textbook chapter from PDF to structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  uv run python -m extract.pdf_to_json \\
      --pdf chapters/physics_11_ch7.pdf \\
      --curriculum ncert --subject physics --grade 11 \\
      --chapter-number 7 \\
      --textbook-name "Physics Part I" \\
      --output data/ncert_physics_11_ch7.json
        """,
    )

    parser.add_argument("--pdf", required=True, help="Path to the chapter PDF (one chapter per PDF)")
    parser.add_argument("--curriculum", required=True, help="Curriculum ID (e.g., 'ncert')")
    parser.add_argument("--subject", required=True, help="Subject ID (e.g., 'physics')")
    parser.add_argument("--grade", type=int, required=True, help="Grade/class number")
    parser.add_argument("--chapter-number", type=int, required=True, help="Chapter number")
    parser.add_argument("--textbook-name", required=True, help="Textbook title")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--model", default="gemini-3-flash-preview", help="Gemini model to use (default: gemini-3-flash-preview)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress file if it exists")

    args = parser.parse_args()

    extract_chapter(
        pdf_path=args.pdf,
        curriculum=args.curriculum,
        subject=args.subject,
        grade=args.grade,
        chapter_number=args.chapter_number,
        textbook_name=args.textbook_name,
        output_path=args.output,
        model=args.model,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
