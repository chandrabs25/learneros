#!/usr/bin/env python3
"""
Generate and upload missing chapter cover images to Cloudflare R2.

This script:
1) Discovers all chapters from the curriculum API.
2) Computes deterministic key names.
3) Checks if each cover already exists in R2.
4) Generates only missing covers with Gemini image model.
5) Converts output to JPEG and uploads to R2.

Deterministic key format:
  chapter-covers/grade-{grade}/{subject-slug}/chapter-{NN}-{chapter-title-slug}.jpg

Required env:
  - GEMINI_API_KEY (or GOOGLE_API_KEY)
  - R2_ACCESS_KEY_ID (or AWS_ACCESS_KEY_ID)
  - R2_SECRET_ACCESS_KEY (or AWS_SECRET_ACCESS_KEY)
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import boto3
from botocore.exceptions import ClientError
from PIL import Image

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


DEFAULT_API_URL = "https://api.learneros.me"
DEFAULT_MODEL = "gemini-3-pro-image-preview"
DEFAULT_R2_BUCKET_URL = "https://1cc208854066dff7ac453aee9a4a0b20.r2.cloudflarestorage.com/learneros"
DEFAULT_R2_PREFIX = "chapter-covers"
DEFAULT_REPORT_FILE = "chapter_cover_sync_report.csv"


@dataclass
class ChapterEntry:
    grade: str
    subject_name: str
    subject_slug: str
    chapter_number: str
    chapter_title: str


def slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "untitled"


def parse_bucket_url(bucket_url: str) -> tuple[str, str]:
    parsed = urlparse(bucket_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid R2 bucket URL: {bucket_url}")
    endpoint_url = f"{parsed.scheme}://{parsed.netloc}"
    bucket = parsed.path.strip("/")
    if not bucket:
        raise ValueError(f"Missing bucket name in URL: {bucket_url}")
    return endpoint_url, bucket


def fetch_json(url: str, timeout_s: float = 60.0) -> Any:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_s) as resp:  # nosec - operator-controlled URL
        return json.loads(resp.read().decode("utf-8"))


def chapter_sort_key(chapter_number: str) -> tuple[int, str]:
    try:
        return (int(chapter_number), chapter_number)
    except (TypeError, ValueError):
        return (10_000, str(chapter_number))


def discover_all_chapters(api_url: str) -> list[ChapterEntry]:
    grades = fetch_json(f"{api_url.rstrip('/')}/api/grades")
    results: list[ChapterEntry] = []

    for g in grades or []:
        grade = str(g.get("grade") or "").strip()
        if not grade:
            continue
        subjects = fetch_json(f"{api_url.rstrip('/')}/api/grades/{quote(grade)}/subjects")
        for s in subjects or []:
            subject_name = str(s.get("name") or "").strip()
            if not subject_name:
                continue
            subject_slug = slugify(subject_name)
            chapters = fetch_json(
                f"{api_url.rstrip('/')}/api/grades/{quote(grade)}/subjects/{quote(subject_name)}/chapters"
            )
            for ch in chapters or []:
                ch_num = str(ch.get("number") or "").strip()
                ch_title = str(ch.get("title") or "").strip()
                if not ch_num or not ch_title:
                    continue
                results.append(
                    ChapterEntry(
                        grade=grade,
                        subject_name=subject_name,
                        subject_slug=subject_slug,
                        chapter_number=ch_num,
                        chapter_title=ch_title,
                    )
                )

    results.sort(
        key=lambda c: (
            int(c.grade) if c.grade.isdigit() else 10_000,
            c.subject_slug,
            chapter_sort_key(c.chapter_number),
        )
    )
    return results


def key_for_cover(prefix: str, ch: ChapterEntry) -> str:
    chapter_n = f"{int(ch.chapter_number):02d}" if str(ch.chapter_number).isdigit() else str(ch.chapter_number).zfill(2)
    title_slug = slugify(ch.chapter_title)
    return f"{prefix.strip('/')}/grade-{ch.grade}/{ch.subject_slug}/chapter-{chapter_n}-{title_slug}.jpg"


def exists_in_r2(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def build_prompt(ch: ChapterEntry, size_hint: str, style_hint: str) -> str:
    return (
        "Create a high-quality educational textbook chapter cover illustration.\n"
        f"Context:\n- Grade: {ch.grade}\n- Subject: {ch.subject_name}\n"
        f"- Chapter: {ch.chapter_number}. {ch.chapter_title}\n\n"
        "Constraints:\n"
        "- Style: clean, modern, textbook-appropriate.\n"
        "- No text overlays, no letters, no numbers.\n"
        "- School-safe imagery only.\n"
        "- Keep composition centered and clear.\n"
        f"- Target aspect ratio: {size_hint} (landscape).\n"
        f"- Style hint: {style_hint}\n"
    )


def generate_image_bytes(api_key: str, model: str, prompt: str, timeout_s: float = 180.0) -> bytes:
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
        with urlopen(req, timeout=timeout_s) as resp:  # nosec - TLS endpoint fixed
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gemini API network error: {exc}") from exc

    for cand in body.get("candidates") or []:
        parts = (cand.get("content") or {}).get("parts") or []
        for part in parts:
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise RuntimeError("No image data returned by Gemini.")


def to_jpeg_bytes(raw_image: bytes, quality: int = 90) -> bytes:
    with Image.open(io.BytesIO(raw_image)) as im:
        converted = im.convert("RGB")
        out = io.BytesIO()
        converted.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate and upload missing chapter covers to R2.")
    p.add_argument("--api-url", default=DEFAULT_API_URL)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--r2-bucket-url", default=DEFAULT_R2_BUCKET_URL)
    p.add_argument("--bucket", default="", help="Optional override bucket name.")
    p.add_argument("--endpoint-url", default="", help="Optional override endpoint URL.")
    p.add_argument("--r2-prefix", default=DEFAULT_R2_PREFIX)
    p.add_argument("--sleep-ms", type=int, default=1000)
    p.add_argument("--size-hint", default="1600x900")
    p.add_argument("--style-hint", default="cinematic science illustration with subtle depth and soft lighting")
    p.add_argument("--limit", type=int, default=0, help="Process first N discovered chapters (0=all).")
    p.add_argument("--report-path", default=DEFAULT_REPORT_FILE)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if load_dotenv is not None:
        load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    if not gemini_key and not args.dry_run:
        print("ERROR: GEMINI_API_KEY/GOOGLE_API_KEY missing.", file=sys.stderr)
        return 2

    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip() or os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip() or os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    if (not access_key or not secret_key) and not args.dry_run:
        print("ERROR: R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY missing.", file=sys.stderr)
        return 2

    parsed_endpoint, parsed_bucket = parse_bucket_url(args.r2_bucket_url)
    endpoint_url = args.endpoint_url.strip() or parsed_endpoint
    bucket = args.bucket.strip() or parsed_bucket

    s3 = None
    if not args.dry_run:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )

    chapters = discover_all_chapters(args.api_url)
    if args.limit > 0:
        chapters = chapters[: args.limit]

    print(f"Discovered chapters: {len(chapters)}")
    print(f"Bucket            : {bucket}")
    print(f"Endpoint          : {endpoint_url}")
    print(f"Prefix            : {args.r2_prefix}")

    report_rows: list[dict[str, str]] = []
    existing_count = 0
    uploaded_count = 0
    failed_count = 0

    for i, ch in enumerate(chapters, start=1):
        key = key_for_cover(args.r2_prefix, ch)
        status = "UNKNOWN"
        error_msg = ""
        print(f"[{i}/{len(chapters)}] grade={ch.grade} subject={ch.subject_slug} chapter={ch.chapter_number} {ch.chapter_title}")
        try:
            already = exists_in_r2(s3, bucket, key) if s3 else False
            if already:
                status = "EXISTS"
                existing_count += 1
                print(f"  exists: s3://{bucket}/{key}")
            else:
                if args.dry_run:
                    status = "MISSING_DRY_RUN"
                    print(f"  would generate+upload: s3://{bucket}/{key}")
                else:
                    prompt = build_prompt(ch, size_hint=args.size_hint, style_hint=args.style_hint)
                    raw = generate_image_bytes(gemini_key, args.model, prompt)
                    jpg = to_jpeg_bytes(raw)
                    s3.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=jpg,
                        ContentType="image/jpeg",
                        CacheControl="public, max-age=31536000, immutable",
                    )
                    status = "UPLOADED"
                    uploaded_count += 1
                    print(f"  uploaded: s3://{bucket}/{key} ({len(jpg)} bytes)")
        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            status = "FAILED"
            error_msg = str(exc)
            print(f"  error: {exc}", file=sys.stderr)

        report_rows.append(
            {
                "grade": ch.grade,
                "subject": ch.subject_name,
                "subject_slug": ch.subject_slug,
                "chapter_number": ch.chapter_number,
                "chapter_title": ch.chapter_title,
                "r2_key": key,
                "status": status,
                "error": error_msg,
            }
        )

        if i < len(chapters) and args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    report_path = Path(args.report_path).resolve()
    with report_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "grade",
                "subject",
                "subject_slug",
                "chapter_number",
                "chapter_title",
                "r2_key",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(report_rows)

    print("")
    print(f"Report   : {report_path}")
    print(f"Exists   : {existing_count}")
    print(f"Uploaded : {uploaded_count}")
    print(f"Failed   : {failed_count}")
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())

