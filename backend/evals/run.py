"""Run LearnerOS model evals online or score captured responses offline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opentelemetry import trace

from app.config import settings
from app.services.llm import LLMProvider, llm_service
from app.telemetry import configure_telemetry, shutdown_telemetry
from evals.scorers import score_output


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "datasets" / "smoke.jsonl"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            records.append(value)
    return records


def _default_model(provider: LLMProvider) -> str:
    return {
        "cerebras": settings.CEREBRAS_MODEL,
        "fireworks": settings.FIREWORKS_MODEL,
        "gemini": "gemini-3.1-pro-preview",
    }[provider]


def _captured_responses(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    return {
        str(record["id"]): record["output"]
        for record in _load_jsonl(path)
        if isinstance(record.get("output"), dict)
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    configure_telemetry()
    cases = _load_jsonl(args.dataset)
    captured = _captured_responses(args.responses)
    model = args.model or _default_model(args.provider)
    tracer = trace.get_tracer("learneros.evals")
    results: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case["id"])
        task = str(case["task"])
        expected = case.get("expected") or {}
        with tracer.start_as_current_span("eval.case") as span:
            span.set_attribute("eval.case.id", case_id)
            span.set_attribute("eval.task", task)
            span.set_attribute("gen_ai.system", args.provider)
            span.set_attribute("gen_ai.request.model", model)

            if case_id in captured:
                output = captured[case_id]
                source = "captured"
            elif task == "tutor":
                text = llm_service.generate_text(
                    provider=args.provider,
                    model=model,
                    prompt=str(case["prompt"]),
                    system=case.get("system"),
                    temperature=args.temperature,
                    operation=f"eval_{task}",
                )
                output = {"text": text}
                source = "model"
            else:
                output = llm_service.generate_json(
                    provider=args.provider,
                    model=model,
                    prompt=str(case["prompt"]),
                    system=case.get("system") or "Return only valid JSON matching the requested schema.",
                    temperature=args.temperature,
                    retries=args.retries,
                    operation=f"eval_{task}",
                )
                source = "model"

            score = score_output(task, output, expected)
            span.set_attribute("eval.score", score.value)
            span.set_attribute("eval.passed", score.value >= args.case_threshold)
            results.append(
                {
                    "id": case_id,
                    "task": task,
                    "source": source,
                    "output": output,
                    **score.to_dict(),
                }
            )

    overall = round(sum(item["score"] for item in results) / len(results), 4) if results else 0.0
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "provider": args.provider,
        "model": model,
        "dataset": str(args.dataset),
        "overall_score": overall,
        "case_threshold": args.case_threshold,
        "minimum_score": args.minimum_score,
        "passed": overall >= args.minimum_score and all(item["score"] >= args.case_threshold for item in results),
        "results": results,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--responses", type=Path, help="JSONL captured outputs for offline scoring")
    parser.add_argument("--provider", choices=("cerebras", "fireworks", "gemini"), default="fireworks")
    parser.add_argument("--model")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--case-threshold", type=float, default=0.75)
    parser.add_argument("--minimum-score", type=float, default=0.85)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "latest.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run(args)
        print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
        return 0 if report["passed"] else 1
    finally:
        shutdown_telemetry()


if __name__ == "__main__":
    sys.exit(main())
