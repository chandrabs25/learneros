#!/usr/bin/env python3
"""
Generate chapter cover images using Gemini image generation and save files
with R2-friendly naming.

Supports 2 input modes:
1) Fetch chapters from backend API by grade + subject.
2) Read a JSON manifest of chapters.

Output includes:
- image files on disk
- upload manifest CSV with local path, R2 key, and public URL

Environment:
- GOOGLE_API_KEY or GEMINI_API_KEY (required)

Example:
  python3 scripts/generate_chapter_cover_images.py \
    --grade 12 \
    --subject physics \
    --api-url https://api.learneros.me \
    --output-dir ./generated-covers \
    --r2-prefix chapter-covers \
    --assets-domain https://assets.learneros.me

Manifest JSON format:
[
  {
    "grade": 12,
    "subject": "physics",
    "chapter_number": "1",
    "chapter_title": "Electric Charges and Fields"
  }
]
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_MODEL = "gemini-3-pro-image-preview"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_R2_PREFIX = "chapter-covers"
DEFAULT_ASSETS_DOMAIN = "https://assets.learneros.me"


@dataclass
class ChapterInput:
    grade: str
    subject: str
    chapter_number: str
    chapter_title: str


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "untitled"


def chapter_number_sort_key(ch_num: str) -> tuple[int, str]:
    try:
        return (int(ch_num), ch_num)
    except ValueError:
        return (10_000, ch_num)


def fetch_json(url: str, timeout_s: float = 60.0) -> Any:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_s) as resp:  # nosec - controlled URL input by operator
        return json.loads(resp.read().decode("utf-8"))


def load_chapters_from_api(api_url: str, grade: str, subject: str) -> list[ChapterInput]:
    subject_title = " ".join(word.capitalize() for word in subject.replace("-", " ").split())
    endpoint = f"{api_url.rstrip('/')}/api/grades/{quote(str(grade))}/subjects/{quote(subject_title)}/chapters"
    rows = fetch_json(endpoint)
    chapters: list[ChapterInput] = []
    for row in rows or []:
        number = str(row.get("number") or "").strip()
        title = str(row.get("title") or "").strip()
        if not number or not title:
            continue
        chapters.append(
            ChapterInput(
                grade=str(grade),
                subject=subject,
                chapter_number=number,
                chapter_title=title,
            )
        )
    chapters.sort(key=lambda c: chapter_number_sort_key(c.chapter_number))
    return chapters


def load_chapters_from_manifest(path: Path) -> list[ChapterInput]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Manifest must be a JSON array.")
    chapters: list[ChapterInput] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        grade = str(item.get("grade") or "").strip()
        subject = str(item.get("subject") or "").strip()
        chapter_number = str(item.get("chapter_number") or "").strip()
        chapter_title = str(item.get("chapter_title") or "").strip()
        if not (grade and subject and chapter_number and chapter_title):
            continue
        chapters.append(
            ChapterInput(
                grade=grade,
                subject=subject,
                chapter_number=chapter_number,
                chapter_title=chapter_title,
            )
        )
    chapters.sort(key=lambda c: (c.grade, slugify(c.subject), chapter_number_sort_key(c.chapter_number)))
    return chapters


def build_prompt(ch: ChapterInput, style_hint: str, size_hint: str) -> str:
    return (
        "Create a high-quality educational chapter cover illustration.\n"
        f"Context:\n- Grade: {ch.grade}\n- Subject: {ch.subject}\n"
        f"- Chapter: {ch.chapter_number}. {ch.chapter_title}\n\n"
        "Constraints:\n"
        "- Style: clean, modern, textbook-appropriate, no branding/logos.\n"
        "- Avoid text overlays, letters, or numbers inside the artwork.\n"
        "- Keep central composition so important objects are visible after mild crop.\n"
        f"- Aspect ratio target: {size_hint} (16:9).\n"
        f"- Visual style hint: {style_hint}\n"
        "- Must be safe for school use.\n"
    )


def generate_image_bytes(
    api_key: str,
    model: str,
    prompt: str,
    timeout_s: float = 180.0,
) -> tuple[bytes, str]:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model)}:generateContent?key={quote(api_key)}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    req = Request(
        endpoint,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout_s) as resp:  # nosec - TLS endpoint controlled by script
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gemini API network error: {exc}") from exc

    candidates = body.get("candidates") or []
    for cand in candidates:
        parts = (cand.get("content") or {}).get("parts") or []
        for part in parts:
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                mime = inline.get("mimeType") or "image/png"
                return base64.b64decode(inline["data"]), mime
    raise RuntimeError(f"No image returned by model. Response keys: {list(body.keys())}")


def ext_for_mime(mime: str) -> str:
    mapping = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }
    return mapping.get(mime.lower(), "png")


def r2_key_for_chapter(prefix: str, ch: ChapterInput, ext: str) -> str:
    return (
        f"{prefix.strip('/')}/"
        f"grade-{ch.grade}/"
        f"{slugify(ch.subject)}/"
        f"chapter-{ch.chapter_number.zfill(2)}-{slugify(ch.chapter_title)}.{ext}"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate chapter cover images using Gemini image model.")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini image model. Default: {DEFAULT_MODEL}")
    p.add_argument("--api-url", default=DEFAULT_API_URL, help="Backend API base URL for chapter fetch mode.")
    p.add_argument("--grade", help="Grade for API chapter fetch mode.")
    p.add_argument("--subject", help="Subject slug/name for API chapter fetch mode (e.g., physics).")
    p.add_argument("--manifest-json", help="Path to JSON manifest (alternative input mode).")
    p.add_argument("--output-dir", default="./chapter-cover-output", help="Directory to write generated images.")
    p.add_argument("--r2-prefix", default=DEFAULT_R2_PREFIX, help=f"R2 object key prefix. Default: {DEFAULT_R2_PREFIX}")
    p.add_argument("--assets-domain", default=DEFAULT_ASSETS_DOMAIN, help=f"Public assets domain. Default: {DEFAULT_ASSETS_DOMAIN}")
    p.add_argument("--manifest-out", default="upload_manifest.csv", help="Output CSV filename (inside output dir).")
    p.add_argument("--sleep-ms", type=int, default=1200, help="Delay between requests in ms.")
    p.add_argument("--style-hint", default="cinematic science illustration with subtle depth and soft lighting", help="Global style hint added to prompts.")
    p.add_argument("--size-hint", default="1600x900", help="Target generation size hint in prompt.")
    p.add_argument("--limit", type=int, default=0, help="Generate only first N chapters (0 = all).")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    p.add_argument("--dry-run", action="store_true", help="Do not call Gemini; only print planned outputs.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        print("ERROR: GOOGLE_API_KEY/GEMINI_API_KEY is not set.", file=sys.stderr)
        return 2

    if bool(args.manifest_json) == bool(args.grade and args.subject):
        print(
            "ERROR: Choose exactly one input mode:\n"
            "  - --manifest-json <file>\n"
            "  - --grade <grade> --subject <subject> [--api-url ...]",
            file=sys.stderr,
        )
        return 2

    if args.manifest_json:
        chapters = load_chapters_from_manifest(Path(args.manifest_json))
    else:
        chapters = load_chapters_from_api(args.api_url, str(args.grade), str(args.subject))

    if not chapters:
        print("No chapters found to process.")
        return 0

    if args.limit > 0:
        chapters = chapters[: args.limit]

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / args.manifest_out

    print(f"Model      : {args.model}")
    print(f"Chapters   : {len(chapters)}")
    print(f"Output dir : {out_dir}")
    print(f"R2 prefix  : {args.r2_prefix}")
    print(f"Assets URL : {args.assets_domain.rstrip('/')}")
    print("")

    rows_for_csv: list[dict[str, str]] = []
    failures = 0

    for idx, ch in enumerate(chapters, start=1):
        prompt = build_prompt(ch, style_hint=args.style_hint, size_hint=args.size_hint)
        temp_ext = "png"
        temp_key = r2_key_for_chapter(args.r2_prefix, ch, temp_ext)
        print(f"[{idx}/{len(chapters)}] {ch.grade} {ch.subject} ch{ch.chapter_number}: {ch.chapter_title}")

        if args.dry_run:
            print(f"  DRY RUN key: {temp_key}")
            continue

        try:
            image_bytes, mime = generate_image_bytes(api_key=api_key, model=args.model, prompt=prompt)
            ext = ext_for_mime(mime)
            r2_key = r2_key_for_chapter(args.r2_prefix, ch, ext)
            local_path = out_dir / r2_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            if local_path.exists() and not args.overwrite:
                print(f"  Skipped existing: {local_path}")
            else:
                local_path.write_bytes(image_bytes)
                print(f"  Wrote: {local_path} ({len(image_bytes)} bytes, {mime})")

            rows_for_csv.append(
                {
                    "grade": ch.grade,
                    "subject": ch.subject,
                    "chapter_number": ch.chapter_number,
                    "chapter_title": ch.chapter_title,
                    "mime_type": mime,
                    "r2_key": r2_key,
                    "local_file": str(local_path),
                    "public_url": f"{args.assets_domain.rstrip('/')}/{r2_key}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ERROR: {exc}", file=sys.stderr)

        if idx < len(chapters) and args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    if rows_for_csv:
        with manifest_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "grade",
                    "subject",
                    "chapter_number",
                    "chapter_title",
                    "mime_type",
                    "r2_key",
                    "local_file",
                    "public_url",
                ],
            )
            writer.writeheader()
            writer.writerows(rows_for_csv)
        print("")
        print(f"Wrote upload manifest: {manifest_path}")

    if failures:
        print(f"Completed with {failures} failures.")
        return 1

    print("Completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
