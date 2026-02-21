#!/usr/bin/env python3
"""Diagnose Kimi (NVIDIA endpoint) configuration and connectivity.

Checks:
1. Environment loading from repo/.env and repo/backend/.env
2. Required vars presence and basic sanity
3. Optional model listing call: GET /models
4. Minimal chat call: POST /chat/completions

Exit code:
- 0 on success
- 1 on configuration or integration failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def load_env() -> None:
    root = Path(__file__).resolve().parent.parent
    backend = root / "backend"
    if load_dotenv is not None:
        load_dotenv(root / ".env")
        load_dotenv(backend / ".env")
        return
    _load_env_fallback(root / ".env")
    _load_env_fallback(backend / ".env")


def _load_env_fallback(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def mask_secret(value: str) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def validate_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def http_get_json(url: str, headers: dict[str, str], timeout_s: float) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {"raw": body}
        return exc.code, payload


def http_post_json(url: str, headers: dict[str, str], payload: dict, timeout_s: float) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except Exception:
            parsed = {"raw": body}
        return exc.code, parsed


def extract_error_message(payload: dict) -> str:
    if not isinstance(payload, dict):
        return str(payload)
    err = payload.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or payload)
    if isinstance(err, str):
        return err
    if "message" in payload:
        return str(payload["message"])
    return json.dumps(payload)[:500]


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Kimi configuration via NVIDIA OpenAI-compatible endpoint.")
    parser.add_argument("--base-url", default=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"))
    parser.add_argument("--model", default=os.getenv("NVIDIA_KIMI_MODEL", "moonshotai/kimi-k2-instruct"))
    parser.add_argument("--api-key-env", default="NVIDIA_API_KEY", help="Environment variable name for API key.")
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-chat", action="store_true")
    args = parser.parse_args()

    load_env()

    api_key = os.getenv(args.api_key_env, "")
    base_url = args.base_url.rstrip("/")
    model = args.model

    print("=== Kimi Config Diagnostics ===")
    print(f"api_key_env  : {args.api_key_env}")
    print(f"api_key      : {mask_secret(api_key)}")
    print(f"base_url     : {base_url}")
    print(f"model        : {model}")
    print(f"timeout_s    : {args.timeout_s}")

    ok = True

    if not api_key:
        print("\n[FAIL] Missing API key.")
        print(f"Set `{args.api_key_env}` in /Users/srichandrasamanapalli/code/AI TUTOR/.env or backend/.env.")
        return 1

    if not validate_url(base_url):
        print("\n[FAIL] Invalid base URL.")
        print("Expected format like: https://integrate.api.nvidia.com/v1")
        return 1

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if not args.skip_models:
        print("\n[STEP] GET /models")
        status, payload = http_get_json(f"{base_url}/models", headers=headers, timeout_s=args.timeout_s)
        if 200 <= status < 300:
            items = payload.get("data", []) if isinstance(payload, dict) else []
            ids = [m.get("id") for m in items if isinstance(m, dict) and "id" in m]
            print(f"[OK] /models status={status}, listed_models={len(ids)}")
            if ids and model not in ids:
                print(f"[WARN] Configured model `{model}` not found in listed models.")
                print("       Use one of the listed IDs or update NVIDIA_KIMI_MODEL.")
                for mid in ids[:20]:
                    print(f"       - {mid}")
        else:
            ok = False
            print(f"[FAIL] /models status={status}")
            print(f"       {extract_error_message(payload)}")

    if not args.skip_chat:
        print("\n[STEP] POST /chat/completions")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": 'Respond with {"ok": true, "msg": "kimi test"}'},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        start = time.perf_counter()
        status, resp_payload = http_post_json(
            f"{base_url}/chat/completions",
            headers=headers,
            payload=payload,
            timeout_s=args.timeout_s,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        if 200 <= status < 300:
            content = ""
            try:
                content = resp_payload["choices"][0]["message"]["content"]
                parsed = json.loads(content) if isinstance(content, str) else content
                print(f"[OK] /chat/completions status={status} latency_ms={latency_ms:.1f}")
                print(f"     response={parsed}")
            except Exception:
                ok = False
                print(f"[FAIL] /chat/completions returned non-parseable content latency_ms={latency_ms:.1f}")
                print(f"       raw_content={content}")
        else:
            ok = False
            print(f"[FAIL] /chat/completions status={status} latency_ms={latency_ms:.1f}")
            msg = extract_error_message(resp_payload)
            print(f"       {msg}")
            if status in (401, 403):
                print("       Hint: invalid key, wrong project, or missing NVIDIA model permission.")
            elif status in (400, 404):
                print("       Hint: wrong model id or incompatible endpoint path.")

    print("\n=== Result ===")
    if ok:
        print("[PASS] Kimi integration config looks good.")
        return 0
    print("[FAIL] One or more checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
