#!/usr/bin/env python3
"""Benchmark model performance for mock insight reconciliation.

Metrics:
- Instruction adherence (strict JSON + schema validity)
- Speed (request latency)

Models under test (defaults):
- minimax-m3-fireworks (served via Fireworks OpenAI-compatible endpoint)

Env vars:
- FIREWORKS_API_KEY
- FIREWORKS_BASE_URL (default: https://api.fireworks.ai/inference/v1)
- FIREWORKS_MODEL (default: accounts/fireworks/models/minimax-m3)
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.request
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


MODEL_ALIASES = {
    "minimax-m3": {"provider": "fireworks", "model_id": None},
    "minimax-m3-fireworks": {"provider": "fireworks", "model_id": None},
}

VALID_TYPES = {"COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"}
REQUIRED_KEYS = {"action", "type", "content"}
VALID_ACTIONS = {"REPLACE", "MERGE"}

MOCK_CASES = [
    {
        "id": "reconcile_case_1",
        "old_type": "MISCONCEPTION",
        "old_content": "Student believes induced current supports the change in magnetic flux.",
        "new_type": "COMPETENCY",
        "new_content": "Student correctly explains Lenz's law and says induced current opposes flux change.",
    },
    {
        "id": "reconcile_case_2",
        "old_type": "PARTIAL_UNDERSTANDING",
        "old_content": "Student knows flux change causes emf but misses direction reasoning.",
        "new_type": "PARTIAL_UNDERSTANDING",
        "new_content": "Student gives direction reasoning but still mixes up sign convention in one step.",
    },
    {
        "id": "reconcile_case_3",
        "old_type": "COMPETENCY",
        "old_content": "Student accurately defines resistivity as intrinsic material property.",
        "new_type": "MISCONCEPTION",
        "new_content": "Student claims resistivity increases with wire length, confusing it with resistance.",
    },
]


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


def build_prompt(case: dict[str, Any]) -> str:
    return f"""Respond in STRICT JSON with exactly this schema:
{{
  "action": "REPLACE or MERGE",
  "type": "COMPETENCY or PARTIAL_UNDERSTANDING or MISCONCEPTION",
  "content": "Reconciled insight text"
}}

Do not output markdown, code fences, or additional keys.

You have two learning insights about the SAME concept for the SAME student.

EXISTING INSIGHT (from an earlier assessment):
  type: {case["old_type"]}
  content: "{case["old_content"]}"

NEW INSIGHT (from the current assessment):
  type: {case["new_type"]}
  content: "{case["new_content"]}"

Insight types:
- COMPETENCY: student demonstrates solid understanding
- PARTIAL_UNDERSTANDING: student understands some aspects but has gaps
- MISCONCEPTION: student holds a factually incorrect belief

Decision policy:
1. If the new insight directly contradicts the old one, use action "REPLACE".
2. If both are compatible (different, non-contradictory facets), use action "MERGE".
3. For MERGE, preserve all still-valid evidence from both insights in content.
4. For REPLACE, content should reflect the latest assessment.
5. Final type must reflect unresolved understanding level:
   - both competency -> COMPETENCY
   - any gap without clear misconception -> PARTIAL_UNDERSTANDING
   - unresolved factual error -> MISCONCEPTION
"""


class LLMRunner:
    def __init__(self, temperature: float, timeout_s: float):
        self.temperature = temperature
        self.timeout_s = timeout_s
        self._fireworks_client: Any | None = None

    def generate(self, model_alias: str, prompt: str) -> str:
        if model_alias not in MODEL_ALIASES:
            raise ValueError(f"Unknown model alias: {model_alias}")
        spec = MODEL_ALIASES[model_alias]
        provider = spec["provider"]
        if provider == "fireworks":
            return self._generate_fireworks(prompt)
        raise ValueError(f"Unsupported provider: {provider}")

    def _generate_fireworks(self, prompt: str) -> str:
        if OpenAI is None:
            raise RuntimeError("openai SDK is not installed. Run: pip install openai")
        api_key = os.getenv("FIREWORKS_API_KEY", "")
        if not api_key:
            raise RuntimeError("FIREWORKS_API_KEY is missing.")
        base_url = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
        model_id = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/minimax-m3")

        if self._fireworks_client is None:
            self._fireworks_client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )

        response = self._fireworks_client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "Return only strict JSON, with no extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
            timeout=self.timeout_s,
        )
        content = response.choices[0].message.content
        return (content or "").strip()


def evaluate_adherence(raw_text: str) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "json_parseable": False,
        "required_keys_present": False,
        "no_extra_keys": False,
        "action_valid": False,
        "type_valid": False,
        "content_valid": False,
    }
    details: dict[str, Any] = {}

    try:
        data = json.loads(raw_text)
        checks["json_parseable"] = True
    except Exception as exc:
        details["parse_error"] = str(exc)
        return {
            "checks": checks,
            "adherence_score": 0.0,
            "strict_pass": False,
            "details": details,
        }

    keys = set(data.keys()) if isinstance(data, dict) else set()
    checks["required_keys_present"] = REQUIRED_KEYS.issubset(keys)
    checks["no_extra_keys"] = keys == REQUIRED_KEYS
    checks["action_valid"] = data.get("action") in VALID_ACTIONS
    checks["type_valid"] = data.get("type") in VALID_TYPES
    content = data.get("content")
    checks["content_valid"] = isinstance(content, str) and bool(content.strip())

    passed = sum(1 for ok in checks.values() if ok)
    adherence_score = passed / len(checks)
    strict_pass = all(checks.values())
    return {
        "checks": checks,
        "adherence_score": adherence_score,
        "strict_pass": strict_pass,
        "details": details,
    }


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    idx = int(0.95 * (len(ordered) - 1))
    return ordered[idx]


def run_benchmark(models: list[str], runs: int, temperature: float, timeout_s: float, verbose: bool) -> dict[str, Any]:
    runner = LLMRunner(temperature=temperature, timeout_s=timeout_s)
    records: list[dict[str, Any]] = []

    for model_alias in models:
        for run_idx in range(1, runs + 1):
            for case in MOCK_CASES:
                prompt = build_prompt(case)
                start = time.perf_counter()
                error = None
                raw = ""
                try:
                    raw = runner.generate(model_alias, prompt)
                except Exception as exc:
                    error = str(exc)
                latency_ms = (time.perf_counter() - start) * 1000

                adherence = (
                    evaluate_adherence(raw)
                    if error is None
                    else {
                        "checks": {},
                        "adherence_score": 0.0,
                        "strict_pass": False,
                        "details": {"request_error": error},
                    }
                )

                row = {
                    "model": model_alias,
                    "run": run_idx,
                    "case_id": case["id"],
                    "latency_ms": latency_ms,
                    "error": error,
                    "adherence_score": adherence["adherence_score"],
                    "strict_pass": adherence["strict_pass"],
                    "checks": adherence["checks"],
                    "details": adherence["details"],
                }
                records.append(row)
                if verbose:
                    print(
                        f"[{model_alias}] run={run_idx} case={case['id']} "
                        f"latency_ms={latency_ms:.1f} strict={row['strict_pass']} err={bool(error)}"
                    )

    summary: dict[str, Any] = {}
    for model_alias in models:
        rows = [r for r in records if r["model"] == model_alias]
        latencies = [r["latency_ms"] for r in rows]
        adherence_scores = [r["adherence_score"] for r in rows]
        strict_count = sum(1 for r in rows if r["strict_pass"])
        err_count = sum(1 for r in rows if r["error"] is not None)
        summary[model_alias] = {
            "total_requests": len(rows),
            "request_errors": err_count,
            "strict_pass_rate": (strict_count / len(rows)) if rows else 0.0,
            "avg_adherence_score": statistics.mean(adherence_scores) if adherence_scores else 0.0,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0.0,
            "p95_latency_ms": p95(latencies),
        }

    return {"records": records, "summary": summary}


def print_summary(result: dict[str, Any]) -> None:
    print("\n=== Mock Reconcile Benchmark Summary ===")
    print(
        f"{'MODEL':30} {'REQ':>5} {'ERR':>5} {'STRICT%':>10} "
        f"{'ADHERE':>8} {'AVG_MS':>10} {'P95_MS':>10}"
    )
    for model, stats in result["summary"].items():
        print(
            f"{model:30} "
            f"{stats['total_requests']:5d} "
            f"{stats['request_errors']:5d} "
            f"{stats['strict_pass_rate'] * 100:9.1f}% "
            f"{stats['avg_adherence_score']:8.3f} "
            f"{stats['avg_latency_ms']:10.1f} "
            f"{stats['p95_latency_ms']:10.1f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mock benchmark for insight reconciliation prompts.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["minimax-m3-fireworks"],
        help=f"Model aliases. Supported: {', '.join(MODEL_ALIASES.keys())}",
    )
    parser.add_argument("--runs", type=int, default=3, help="Runs per mock case per model.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    parser.add_argument("--timeout-s", type=float, default=60.0, help="Request timeout in seconds.")
    parser.add_argument("--output-json", default="", help="Optional path to write full benchmark JSON.")
    parser.add_argument("--verbose", action="store_true", help="Print per-request details.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env()

    unsupported = [m for m in args.models if m not in MODEL_ALIASES]
    if unsupported:
        raise SystemExit(f"Unsupported model aliases: {unsupported}")
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")

    result = run_benchmark(
        models=args.models,
        runs=args.runs,
        temperature=args.temperature,
        timeout_s=args.timeout_s,
        verbose=args.verbose,
    )
    print_summary(result)

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nSaved detailed output to: {out_path}")


if __name__ == "__main__":
    main()
