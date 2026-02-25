"""
Merge progress JSONs into final chapter JSONs.
Self-contained — copies the merge logic to avoid import issues.

Usage:
  python3 scripts/merge_progress.py
"""

import json
import re
import sys
from pathlib import Path

# ===== Copied from extract/pdf_to_json.py =====

def _titles_match(title_a: str, title_b: str) -> bool:
    a = title_a.strip().lower()
    b = title_b.strip().lower()
    if a == b:
        return True
    if a in b or b in a:
        return True
    for suffix in [" (continued)", " (contd)", " continued", " contd", " cont"]:
        a_clean = a.removesuffix(suffix)
        b_clean = b.removesuffix(suffix)
        if a_clean == b_clean:
            return True
    return False


def _normalize_concept_ref(ref: str) -> str:
    s = ref.strip()
    if s.lower().startswith("concept:"):
        s = s[len("concept:"):]
    s = s.lower()
    s = s.replace("'", "").replace("\u2019", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
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
    merged_sections: dict[str, dict] = {}
    all_exercises: list[dict] = []
    exercise_title = "Exercises"

    for chunk in chunks:
        for sec in chunk.get("sections", []):
            sec_num = sec["number"]
            if sec_num not in merged_sections:
                merged_sections[sec_num] = {
                    "number": sec_num,
                    "title": sec["title"],
                    "subsections": [],
                    "prerequisites": sec.get("prerequisites", []),
                }
            existing = merged_sections[sec_num]
            new_subs = sec.get("subsections", [])
            if existing["subsections"] and new_subs:
                last_existing = existing["subsections"][-1]
                first_new = new_subs[0]
                if last_existing.get("content_text", "").endswith("[CONTINUES]"):
                    last_existing["content_text"] = (
                        last_existing["content_text"][:-len("[CONTINUES]")].rstrip()
                        + " " + first_new.get("content_text", "")
                    )
                    last_existing.setdefault("worked_examples", []).extend(first_new.get("worked_examples", []))
                    last_existing.setdefault("diagrams", []).extend(first_new.get("diagrams", []))
                    last_existing.setdefault("tables", []).extend(first_new.get("tables", []))
                    new_subs = new_subs[1:]
            existing["subsections"].extend(new_subs)

            existing_prereq_refs = {p.get("ref") for p in existing.get("prerequisites", []) if p.get("ref")}
            for prereq in sec.get("prerequisites", []):
                if not prereq.get("ref") or not prereq.get("type"):
                    continue
                if prereq["ref"] not in existing_prereq_refs:
                    existing["prerequisites"].append(prereq)
                    existing_prereq_refs.add(prereq["ref"])

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
            all_exercises[i + 1]["problem"] = ""
    all_exercises = [e for e in all_exercises if e.get("problem")]

    # Post-merge: combine consecutive same-titled subsections
    for sec in merged_sections.values():
        if len(sec["subsections"]) < 2:
            continue
        merged_subs = [sec["subsections"][0]]
        for sub in sec["subsections"][1:]:
            prev = merged_subs[-1]
            same_title = _titles_match(prev.get("title", ""), sub.get("title", ""))
            continues = prev.get("content_text", "").rstrip().endswith("[CONTINUES]")
            if same_title or continues:
                prev_text = prev.get("content_text", "")
                if prev_text.rstrip().endswith("[CONTINUES]"):
                    prev_text = prev_text.rstrip()[:-len("[CONTINUES]")].rstrip()
                prev["content_text"] = prev_text + "\n" + sub.get("content_text", "")
                prev.setdefault("worked_examples", []).extend(sub.get("worked_examples", []))
                prev.setdefault("diagrams", []).extend(sub.get("diagrams", []))
                prev.setdefault("tables", []).extend(sub.get("tables", []))
            else:
                merged_subs.append(sub)
        sec["subsections"] = merged_subs

    # Re-number subsection orders
    for sec in merged_sections.values():
        for idx, sub in enumerate(sec["subsections"], 1):
            sub["order"] = idx

    # Deduplicate exercises
    seen_ex = set()
    deduped_exercises = []
    for ex in all_exercises:
        if ex["number"] not in seen_ex:
            seen_ex.add(ex["number"])
            deduped_exercises.append(ex)

    # Fix content_type
    valid_content_types = {"explanation", "derivation", "law", "definition", "theorem", "experiment", "application"}
    for sec in merged_sections.values():
        for sub in sec.get("subsections", []):
            if sub.get("content_type", "") not in valid_content_types:
                sub["content_type"] = "explanation"

    # Fix exercise_type
    valid_exercise_types = {"conceptual", "numerical", "derivation", "mcq", "short_answer", "long_answer"}
    for ex in deduped_exercises:
        if ex.get("exercise_type", "") not in valid_exercise_types:
            ex["exercise_type"] = "conceptual"

    # Normalize references
    id_prefix = f"{curriculum}:{subject}:{grade}:{chapter_number}"
    for sec in merged_sections.values():
        normalized_prereqs = []
        seen_refs = set()
        for prereq in sec.get("prerequisites", []):
            if not prereq.get("type") or not prereq.get("ref"):
                continue
            if prereq["type"] == "concept":
                prereq["ref"] = _normalize_concept_ref(prereq["ref"])
            elif prereq["type"] == "section":
                ref = prereq["ref"].strip()
                if re.match(r"^[\d.]+$", ref) or ref.upper() == "SUMMARY":
                    ref = f"{id_prefix}:{ref}"
                elif ref.startswith(id_prefix + ":"):
                    suffix = ref[len(id_prefix) + 1:]
                    if ":" in suffix:
                        suffix = suffix.replace(":", ".")
                    ref = f"{id_prefix}:{suffix}"
                prereq["ref"] = ref
            if prereq["ref"] not in seen_refs:
                seen_refs.add(prereq["ref"])
                normalized_prereqs.append(prereq)
        sec["prerequisites"] = normalized_prereqs

    for ex in deduped_exercises:
        ex["tests"] = [_normalize_concept_ref(tc) for tc in ex.get("tests", [])]

    # Fix difficulty
    valid_difficulties = {"easy", "medium", "hard"}
    for ex in deduped_exercises:
        if ex.get("difficulty", "") not in valid_difficulties:
            ex["difficulty"] = "medium"

    return {
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

# ===== End copied logic =====


CHAPTERS = [
    {
        "progress_path": "data/ncert_chemistry_11_ch5.progress.json",
        "output_path": "data/ncert_chemistry_11_ch5.json",
        "curriculum": "ncert",
        "subject": "chemistry",
        "grade": 11,
        "chapter_number": 5,
        "textbook_name": "Chemistry Part I",
        "chapter_title": "Thermodynamics",
    },
    {
        "progress_path": "data/ncert_chemistry_11_ch8.progress.json",
        "output_path": "data/ncert_chemistry_11_ch8.json",
        "curriculum": "ncert",
        "subject": "chemistry",
        "grade": 11,
        "chapter_number": 8,
        "textbook_name": "Chemistry Part II",
        "chapter_title": "Organic Chemistry – Some Basic Principles and Techniques",
    },
]


def merge_one(cfg: dict):
    progress_path = Path(cfg["progress_path"])
    output_path = Path(cfg["output_path"])

    print(f"\n{'='*60}")
    print(f"📖 Ch{cfg['chapter_number']}: {cfg['chapter_title']}")
    print(f"   Input:  {progress_path}")
    print(f"   Output: {output_path}")
    print(f"{'='*60}")

    with open(progress_path) as f:
        chunks = json.load(f)
    print(f"   Loaded {len(chunks)} page chunks")

    merged = merge_chunks(
        chunks=chunks,
        curriculum=cfg["curriculum"],
        subject=cfg["subject"],
        grade=cfg["grade"],
        chapter_number=cfg["chapter_number"],
        textbook_name=cfg["textbook_name"],
        chapter_title=cfg["chapter_title"],
    )

    # Save
    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # Validate JSON
    with open(output_path) as f:
        json.load(f)

    # Stats
    ch = merged["chapter"]
    secs = ch["sections"]
    total_subs = sum(len(s.get("subsections", [])) for s in secs)
    total_examples = sum(
        len(ss.get("worked_examples", []))
        for s in secs
        for ss in s.get("subsections", [])
    )
    ex = ch.get("exercises") or {}
    total_exercises = len(ex.get("items", []))

    print(f"\n   🎉 Merged successfully!")
    print(f"      Sections:     {len(secs)}")
    print(f"      Subsections:  {total_subs}")
    print(f"      Examples:     {total_examples}")
    print(f"      Exercises:    {total_exercises}")
    print(f"      File size:    {output_path.stat().st_size:,} bytes")

    # Check for any remaining [CONTINUES] or [SKIPPED]
    s = json.dumps(merged)
    issues = []
    if "[CONTINUES]" in s:
        issues.append("[CONTINUES] markers remain")
    if "[SKIPPED" in s:
        issues.append("[SKIPPED] markers remain")
    if issues:
        print(f"      ⚠️  Issues: {', '.join(issues)}")
    else:
        print(f"      ✅ No [CONTINUES] or [SKIPPED] markers")

    return True


def main():
    all_ok = True
    for cfg in CHAPTERS:
        if not Path(cfg["progress_path"]).exists():
            print(f"⚠️  Skipping ch{cfg['chapter_number']}: {cfg['progress_path']} not found")
            continue
        if not merge_one(cfg):
            all_ok = False

    if all_ok:
        print(f"\n✅ All chapters merged successfully!")
    else:
        print(f"\n⚠️  Some chapters had issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
