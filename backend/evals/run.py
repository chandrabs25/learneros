"""Run LearnerOS model evals online or score captured responses offline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opentelemetry import trace

from app.config import settings
from app.services.llm import LLMProvider, llm_service
from app.telemetry import configure_telemetry, shutdown_telemetry
from evals.dataset_contract import is_runnable, load_jsonl, validate_case
from evals.scorers import score_output


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "datasets" / "smoke.jsonl"


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
        for record in load_jsonl(path)
        if isinstance(record.get("output"), dict)
    }


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Embedding vectors must have equal, non-zero dimensions")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _run_retrieval(case: dict[str, Any]) -> dict[str, Any]:
    inputs = case["input"]
    query = str(inputs["query"])
    candidates = inputs["candidates"]
    top_k = max(1, min(int(inputs.get("top_k", 4)), len(candidates)))
    query_embedding = llm_service.embed(
        provider="fireworks",
        model=settings.FIREWORKS_EMBEDDING_MODEL,
        text=query,
        operation="eval_retrieval_query",
    )
    ranked: list[tuple[float, str]] = []
    for candidate in candidates:
        candidate_embedding = llm_service.embed(
            provider="fireworks",
            model=settings.FIREWORKS_EMBEDDING_MODEL,
            text=str(candidate["content"]),
            operation="eval_retrieval_candidate",
        )
        ranked.append(
            (
                _cosine_similarity(query_embedding, candidate_embedding),
                str(candidate["id"]),
            )
        )
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return {
        "selected_ids": [candidate_id for _, candidate_id in ranked[:top_k]],
        "scores": {candidate_id: round(score, 6) for score, candidate_id in ranked[:top_k]},
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    configure_telemetry()
    loaded_cases = load_jsonl(args.dataset)
    for case in loaded_cases:
        validate_case(case)
    cases = [case for case in loaded_cases if is_runnable(case)]
    skipped_unreviewed = len(loaded_cases) - len(cases)
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
            elif task == "retrieval":
                output = _run_retrieval(case)
                source = "embedding"
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
        "case_count": len(results),
        "skipped_unreviewed": skipped_unreviewed,
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
