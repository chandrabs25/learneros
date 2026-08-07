#!/usr/bin/env python3
"""Benchmark model performance for mock answer evaluation.

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

VALID_INSIGHT_TYPES = {"COMPETENCY", "PARTIAL_UNDERSTANDING", "MISCONCEPTION"}
REQUIRED_EVAL_KEYS = {
    "score",
    "grade",
    "feedback",
    "strengths",
    "improvements",
    "model_answer",
    "insights",
}

MOCK_CASES = [
    {
        "id": "eval_case_1",
        "context": (
            "Magnetic flux is defined as Phi = B·A = BAcos(theta). Faraday's law states that induced emf "
            "is proportional to the rate of change of magnetic flux and direction follows Lenz's law."
        ),
        "question": "Explain why current is induced when a magnet is moved toward a coil.",
        "answer": (
            "Current is induced because moving magnet lines cut the coil and the changing flux produces emf. "
            "Direction opposes change according to Lenz law."
        ),
        "concepts": [
            {"id": "concept:magnetic-flux", "name": "Magnetic Flux"},
            {"id": "concept:faradays-law", "name": "Faraday's Law"},
            {"id": "concept:lenzs-law", "name": "Lenz's Law"},
        ],
    },
    {
        "id": "eval_case_2",
        "context": (
            "Newton's first law states that a body remains in uniform motion unless acted upon by net force. "
            "Inertia is resistance to change in state of motion."
        ),
        "question": "What is inertia and how is it related to Newton's first law?",
        "answer": "Inertia is force that keeps object moving. It equals mass times acceleration.",
        "concepts": [
            {"id": "concept:inertia", "name": "Inertia"},
            {"id": "concept:newtons-first-law", "name": "Newton's First Law"},
        ],
    },
    {
        "id": "eval_case_3",
        "context": (
            "Ohm's law: V = IR. Resistivity is an intrinsic property and depends on material and temperature. "
            "Resistance depends on resistivity, length, and area: R = rho L / A."
        ),
        "question": "Differentiate resistance and resistivity with one practical implication.",
        "answer": (
            "Resistance depends on dimensions and material, while resistivity is only material property. "
            "Longer wires increase resistance."
        ),
        "concepts": [
            {"id": "concept:resistance", "name": "Resistance"},
            {"id": "concept:resistivity", "name": "Resistivity"},
        ],
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
    concept_list = "\n".join(
        f'  - concept_id: "{c["id"]}", name: "{c["name"]}"' for c in case["concepts"]
    ) or "  (no concepts linked)"

    return f"""You are an expert teacher evaluating a student's answer.

STUDY MATERIAL (ground truth):
{case["context"]}

QUESTION: {case["question"]}

STUDENT'S ANSWER: {case["answer"]}

CONCEPTS LINKED TO THIS SECTION:
{concept_list}

─── TASK ───

1. Evaluate the student's answer for accuracy, completeness, and depth.
2. Generate learning insights ONLY for concepts that the QUESTION DIRECTLY
   tests and the ANSWER meaningfully addresses (correctly or incorrectly).

CRITICAL RULES FOR INSIGHTS:
- Do NOT create an insight for a concept unless the question specifically
  asks about it AND the student's answer says something about it.
- If a concept is only tangentially related to the question, do NOT include it.
- It is perfectly fine to return an empty insights array if no concepts
  are directly tested.

Insight types:
- COMPETENCY: student demonstrates correct, solid understanding
- PARTIAL_UNDERSTANDING: student has the right idea but misses key details
- MISCONCEPTION: student shows a factually incorrect understanding

Respond in STRICT JSON:
{{
  "score": <number 0-100>,
  "grade": "<A/B/C/D/F>",
  "feedback": "2-3 sentences of constructive feedback",
  "strengths": ["point1", "point2"],
  "improvements": ["point1", "point2"],
  "model_answer": "A brief ideal answer in 2-3 sentences",
  "insights": [
    {{
      "concept_id": "<exact concept_id from the list above>",
      "concept_name": "<concept name>",
      "type": "<COMPETENCY|PARTIAL_UNDERSTANDING|MISCONCEPTION>",
      "category": "conceptual",
      "content": "One sentence describing what the student understood or misunderstood about this concept"
    }}
  ]
}}

Return ONLY valid JSON, no markdown fences, no extra text."""


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
            self._fireworks_client = OpenAI(api_key=api_key, base_url=base_url)

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


def _is_list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _validate_insights(insights: Any) -> bool:
    if not isinstance(insights, list):
        return False
    required = {"concept_id", "concept_name", "type", "category", "content"}
    for item in insights:
        if not isinstance(item, dict):
            return False
        if not required.issubset(item.keys()):
            return False
        if item.get("type") not in VALID_INSIGHT_TYPES:
            return False
        if not isinstance(item.get("category"), str) or not item["category"].strip():
            return False
        if not isinstance(item.get("content"), str) or not item["content"].strip():
            return False
    return True


def evaluate_adherence(raw_text: str) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "json_parseable": False,
        "required_keys_present": False,
        "no_extra_keys": False,
        "score_valid": False,
        "grade_valid": False,
        "strengths_valid": False,
        "improvements_valid": False,
        "insights_valid": False,
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
    checks["required_keys_present"] = REQUIRED_EVAL_KEYS.issubset(keys)
    checks["no_extra_keys"] = keys == REQUIRED_EVAL_KEYS

    score = data.get("score")
    checks["score_valid"] = isinstance(score, (int, float)) and 0 <= float(score) <= 100
    checks["grade_valid"] = data.get("grade") in {"A", "B", "C", "D", "F"}
    checks["strengths_valid"] = _is_list_of_strings(data.get("strengths"))
    checks["improvements_valid"] = _is_list_of_strings(data.get("improvements"))
    checks["insights_valid"] = _validate_insights(data.get("insights"))

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
    print("\n=== Mock Evaluation Benchmark Summary ===")
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
    parser = argparse.ArgumentParser(description="Mock benchmark for answer evaluation prompts.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["minimax-m3"],
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
