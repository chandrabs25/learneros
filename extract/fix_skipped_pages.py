"""
Re-extract skipped page chunks one page at a time, then merge into existing JSONs.

Usage:
    GEMINI_API_KEY="..." uv run python extract/fix_skipped_pages.py
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from extract.pdf_to_json import (
    extract_pages_from_pdf,
    build_page_prompt,
    build_snapshot,
    call_gemini,
)

# =========================================================================
# Skipped chunks to re-extract (Ch14 bibliography excluded)
# =========================================================================

SKIPPED_CHUNKS = [
    {
        "json_file": "data/ncert_physics_12_ch2.json",
        "pdf_file": "chapters/physics_11_ch2.pdf",
        "pages": [13, 14, 15],  # 1-indexed
        "description": "Exercises (problems 2.8+)",
        "curriculum": "ncert", "subject": "physics", "grade": 12,
        "chapter_number": 2,
        "textbook_name": "Electrostatic Potential and Capacitance",
    },
    {
        "json_file": "data/ncert_physics_12_ch9.json",
        "pdf_file": "chapters/physics 12 part 2/leph201.pdf",
        "pages": [31, 32, 33],
        "description": "Exercises (problems 9.18+)",
        "curriculum": "ncert", "subject": "physics", "grade": 12,
        "chapter_number": 9,
        "textbook_name": "Ray Optics and Optical Instruments",
    },
    {
        "json_file": "data/ncert_physics_12_ch5.json",
        "pdf_file": "chapters/physics_11_ch5.pdf",
        "pages": [4, 5, 6],
        "description": "Section content (Magnetism)",
        "curriculum": "ncert", "subject": "physics", "grade": 12,
        "chapter_number": 5,
        "textbook_name": "Magnetism and Matter",
    },
    {
        "json_file": "data/ncert_physics_12_ch6.json",
        "pdf_file": "chapters/physics_11_ch6.pdf",
        "pages": [7, 8, 9],
        "description": "Missing sections 6.5-6.6",
        "curriculum": "ncert", "subject": "physics", "grade": 12,
        "chapter_number": 6,
        "textbook_name": "Electromagnetic Induction",
    },
]


def extract_single_page(
    pdf_path: str,
    page_num: int,  # 1-indexed
    total_pages: int,
    snapshot: str,
    curriculum: str,
    subject: str,
    grade: int,
    chapter_number: int,
    textbook_name: str,
) -> dict:
    """Extract content from a single page using Gemini."""
    # Get page image
    pages = extract_pages_from_pdf(pdf_path)
    if page_num - 1 >= len(pages):
        raise ValueError(f"Page {page_num} out of range (PDF has {len(pages)} pages)")

    page_image = pages[page_num - 1]

    prompt = build_page_prompt(
        page_start=page_num,
        page_end=page_num,
        total_pages=total_pages,
        snapshot=snapshot,
        curriculum=curriculum,
        subject=subject,
        grade=grade,
        chapter_number=chapter_number,
        textbook_name=textbook_name,
    )

    print(f"    🤖 Calling Gemini for page {page_num}...", end=" ", flush=True)
    result = call_gemini(prompt, page_images=[page_image])
    
    n_secs = len(result.get("sections", []))
    n_subs = sum(len(s.get("subsections", [])) for s in result.get("sections", []))
    n_ex = len(result.get("exercises", {}).get("items", []))
    print(f"✅ ({n_secs} secs, {n_subs} subs, {n_ex} exercises)")
    
    return result


def merge_chunks_into_json(json_path: str, chunks: list[dict]) -> dict:
    """Merge extracted page chunks into the existing JSON file."""
    with open(json_path) as f:
        data = json.load(f)

    ch = data["chapter"]
    existing_sections = {s["number"]: s for s in ch.get("sections", [])}
    existing_exercises = (ch.get("exercises") or {}).get("items", [])
    existing_ex_nums = {e["number"] for e in existing_exercises}

    new_sections_added = 0
    new_subs_added = 0
    new_exercises_added = 0

    for chunk in chunks:
        # Merge sections
        for sec in chunk.get("sections", []):
            sec_num = sec["number"]
            if sec_num in existing_sections:
                # Append new subsections to existing section
                existing = existing_sections[sec_num]
                existing_subs = existing.get("subsections", [])
                max_order = max((s.get("order", 0) for s in existing_subs), default=0)
                
                for sub in sec.get("subsections", []):
                    # Check if subsection title already exists
                    existing_titles = {s.get("title", "").lower() for s in existing_subs}
                    if sub.get("title", "").lower() not in existing_titles:
                        sub["order"] = max_order + 1
                        max_order += 1
                        existing_subs.append(sub)
                        new_subs_added += 1
                
                existing["subsections"] = existing_subs
            else:
                # Brand new section — insert in correct position
                new_sections_added += 1
                new_subs_added += len(sec.get("subsections", []))
                
                # Find correct insertion point
                sections_list = ch.get("sections", [])
                insert_idx = len(sections_list)
                
                try:
                    sec_float = float(sec_num)
                    for i, s in enumerate(sections_list):
                        try:
                            if float(s["number"]) > sec_float:
                                insert_idx = i
                                break
                        except (ValueError, TypeError):
                            continue
                except (ValueError, TypeError):
                    pass
                
                sections_list.insert(insert_idx, sec)
                ch["sections"] = sections_list
                existing_sections[sec_num] = sec

        # Merge exercises
        ex_data = chunk.get("exercises") or {}
        new_items = ex_data.get("items", [])
        if new_items:
            if not ch.get("exercises"):
                ch["exercises"] = {"title": "Exercises", "items": []}
            
            for item in new_items:
                if item["number"] not in existing_ex_nums:
                    ch["exercises"]["items"].append(item)
                    existing_ex_nums.add(item["number"])
                    new_exercises_added += 1
            
            # Sort exercises by number
            ch["exercises"]["items"].sort(key=lambda x: x.get("number", 0))

    # Save
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {
        "new_sections": new_sections_added,
        "new_subsections": new_subs_added,
        "new_exercises": new_exercises_added,
    }


def process_skipped_chunk(chunk_info: dict):
    """Process a single skipped chunk: extract page by page, then merge."""
    json_file = chunk_info["json_file"]
    pdf_file = chunk_info["pdf_file"]
    pages = chunk_info["pages"]
    
    print(f"\n{'='*60}")
    print(f"📖 {os.path.basename(json_file)}: {chunk_info['description']}")
    print(f"   PDF: {pdf_file}, pages: {pages}")
    print(f"{'='*60}")

    if not os.path.exists(pdf_file):
        print(f"  ❌ PDF NOT FOUND: {pdf_file}")
        return

    # Load existing JSON to build snapshot context
    with open(json_file) as f:
        data = json.load(f)
    
    ch = data["chapter"]
    
    # Build snapshot from existing sections for context
    existing_chunks = [{"sections": ch.get("sections", []), "exercises": ch.get("exercises")}]

    import fitz
    doc = fitz.open(pdf_file)
    total_pages = len(doc)
    doc.close()

    extracted_chunks = []
    
    for page_num in pages:
        if page_num > total_pages:
            print(f"  ⚠️ Page {page_num} out of range ({total_pages} pages), skipping")
            continue
        
        # Build snapshot including prior extracted pages
        snapshot = build_snapshot(existing_chunks + extracted_chunks)
        
        try:
            result = extract_single_page(
                pdf_path=pdf_file,
                page_num=page_num,
                total_pages=total_pages,
                snapshot=snapshot,
                curriculum=chunk_info["curriculum"],
                subject=chunk_info["subject"],
                grade=chunk_info["grade"],
                chapter_number=chunk_info["chapter_number"],
                textbook_name=chunk_info["textbook_name"],
            )
            extracted_chunks.append(result)
        except Exception as e:
            print(f"  ❌ Error on page {page_num}: {e}")
            continue
        
        # Brief pause between pages
        time.sleep(2)

    if extracted_chunks:
        print(f"\n  📥 Merging {len(extracted_chunks)} page chunks into {os.path.basename(json_file)}...")
        stats = merge_chunks_into_json(json_file, extracted_chunks)
        print(f"  ✅ Merged: {stats}")
    else:
        print(f"  ⚠️ No chunks extracted")


def main():
    for chunk_info in SKIPPED_CHUNKS:
        process_skipped_chunk(chunk_info)
        time.sleep(3)  # Rate limit between chapters
    
    print(f"\n{'='*60}")
    print(f"🎉 ALL SKIPPED CHUNKS PROCESSED!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
