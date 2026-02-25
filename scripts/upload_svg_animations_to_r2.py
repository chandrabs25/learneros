#!/usr/bin/env python3
"""
Upload animation assets to Cloudflare R2 via S3-compatible API.

Default behavior:
- Reads HTML files recursively from ./data/animations
- Uploads to bucket "learneros"
- Writes keys under prefix "animations/"

Examples:
  python3 scripts/upload_svg_animations_to_r2.py

  python3 scripts/upload_svg_animations_to_r2.py \
    --source-dir "./animations" \
    --bucket "learneros" \
    --key-prefix "animations" \
    --endpoint-url "https://1cc208854066dff7ac453aee9a4a0b20.r2.cloudflarestorage.com"

Required credentials (env):
- R2_ACCESS_KEY_ID / AWS_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY / AWS_SECRET_ACCESS_KEY
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    import boto3
except Exception as exc:  # pragma: no cover
    print("ERROR: boto3 is required. Install with: pip install boto3", file=sys.stderr)
    raise


DEFAULT_R2_BUCKET_URL = "https://1cc208854066dff7ac453aee9a4a0b20.r2.cloudflarestorage.com/learneros"
DEFAULT_SOURCE_DIR = "./data/animations"
DEFAULT_KEY_PREFIX = "animations"
DEFAULT_EXTENSIONS = ".html"


def _parse_bucket_url(bucket_url: str) -> tuple[str, str]:
    parsed = urlparse(bucket_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid R2 bucket URL: {bucket_url}")
    endpoint_url = f"{parsed.scheme}://{parsed.netloc}"
    bucket = parsed.path.strip("/")
    if not bucket:
        raise ValueError(f"Bucket name missing in R2 bucket URL: {bucket_url}")
    return endpoint_url, bucket


def _collect_files(source_dir: Path, extensions: set[str]) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(
        p for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in extensions
    )


def _build_key(prefix: str, source_dir: Path, file_path: Path) -> str:
    rel = file_path.relative_to(source_dir).as_posix()
    clean_prefix = prefix.strip("/")
    if clean_prefix:
        return f"{clean_prefix}/{rel}"
    return rel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload animation files to Cloudflare R2 (S3 API).")
    parser.add_argument("--r2-bucket-url", default=DEFAULT_R2_BUCKET_URL, help="R2 bucket URL containing account endpoint + bucket name.")
    parser.add_argument("--endpoint-url", default="", help="Optional explicit endpoint URL (overrides parsed endpoint).")
    parser.add_argument("--bucket", default="", help="Optional explicit bucket name (overrides parsed bucket).")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help=f"Directory containing animation files. Default: {DEFAULT_SOURCE_DIR}")
    parser.add_argument("--key-prefix", default=DEFAULT_KEY_PREFIX, help=f"Destination key prefix in bucket. Default: {DEFAULT_KEY_PREFIX}")
    parser.add_argument(
        "--extensions",
        default=DEFAULT_EXTENSIONS,
        help="Comma-separated file extensions to upload (example: .html,.svg). Default: .html",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned uploads without uploading.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip files whose key already exists in the bucket.")
    parser.add_argument("--public-base-url", default="https://assets.learneros.me", help="Public base URL used for output preview links.")
    return parser.parse_args()


def _content_type_for_suffix(suffix: str) -> str:
    s = suffix.lower()
    if s == ".html":
        return "text/html; charset=utf-8"
    if s == ".svg":
        return "image/svg+xml"
    return "application/octet-stream"


def _list_existing_keys(s3, bucket: str, prefix: str) -> set[str]:
    """List all existing object keys under the given prefix."""
    keys: set[str] = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.add(obj["Key"])
    return keys


def main() -> int:
    args = parse_args()
    if load_dotenv is not None:
        load_dotenv()

    parsed_endpoint, parsed_bucket = _parse_bucket_url(args.r2_bucket_url)
    endpoint_url = args.endpoint_url.strip() or parsed_endpoint
    bucket = args.bucket.strip() or parsed_bucket

    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip() or os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip() or os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

    if not access_key or not secret_key:
        print(
            "ERROR: Missing credentials. Set R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY "
            "or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY.",
            file=sys.stderr,
        )
        return 2

    source_dir = Path(args.source_dir).resolve()
    ext_parts = [e.strip().lower() for e in args.extensions.split(",") if e.strip()]
    normalized_exts = {e if e.startswith(".") else f".{e}" for e in ext_parts}
    if not normalized_exts:
        print("ERROR: --extensions cannot be empty.", file=sys.stderr)
        return 2

    asset_files = _collect_files(source_dir, normalized_exts)
    if not asset_files:
        print(f"No matching files found in: {source_dir} (extensions: {', '.join(sorted(normalized_exts))})")
        return 0

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    print(f"Source dir : {source_dir}")
    print(f"Endpoint   : {endpoint_url}")
    print(f"Bucket     : {bucket}")
    print(f"Key prefix : {args.key_prefix.strip('/') or '(none)'}")
    print(f"Extensions : {', '.join(sorted(normalized_exts))}")
    print(f"Files found: {len(asset_files)}")

    # Fetch existing keys if --skip-existing
    existing_keys: set[str] = set()
    if args.skip_existing:
        print("Listing existing keys in bucket...")
        existing_keys = _list_existing_keys(s3, bucket, args.key_prefix.strip("/"))
        print(f"Existing   : {len(existing_keys)} objects already in bucket")

    uploaded = 0
    skipped = 0
    failed = 0

    for file_path in asset_files:
        key = _build_key(args.key_prefix, source_dir, file_path)
        preview_url = f"{args.public_base_url.rstrip('/')}/{key}"

        if args.skip_existing and key in existing_keys:
            skipped += 1
            continue

        if args.dry_run:
            print(f"[DRY-RUN] {file_path} -> s3://{bucket}/{key} ({preview_url})")
            continue
        try:
            s3.upload_file(
                str(file_path),
                bucket,
                key,
                ExtraArgs={
                    "ContentType": _content_type_for_suffix(file_path.suffix),
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )
            uploaded += 1
            print(f"[OK] {file_path.name} -> s3://{bucket}/{key}")
        except Exception as exc:  # pragma: no cover
            failed += 1
            print(f"[ERR] {file_path} -> s3://{bucket}/{key} :: {exc}", file=sys.stderr)

    print(f"Done. uploaded={uploaded} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
