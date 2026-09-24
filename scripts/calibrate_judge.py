#!/usr/bin/env python
"""Calibrates the local Ollama judge model against the human labels in the golden dataset.

Run this whenever the judge model or prompt changes (e.g. swapping llama3.2:1b for phi3:mini) —
model choice is a tuning decision backed by this number, not a guess. See docs/judge-calibration.md.

Usage:
    python scripts/calibrate_judge.py
    python scripts/calibrate_judge.py --model phi3:mini --min-agreement 0.8
    python scripts/calibrate_judge.py --json > calibration_result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from llm_eval_guard.core.calibration import MetricCalibration, load_and_calibrate
from llm_eval_guard.metrics.deepeval_adapter import (
    PASS_THRESHOLD_DEFAULT,
    answer_relevancy_metric,
    faithfulness_metric,
    judge_model,
)

DEFAULT_DATASET = Path(__file__).parent.parent / "datasets" / "golden" / "sample_rag_qa.jsonl"


def _print_report(calibration: MetricCalibration) -> None:
    r = calibration.pearson_r
    r_str = "n/a" if r is None else f"{r:.2f}"
    print(
        f"{calibration.metric_name}: "
        f"agreement={calibration.pass_fail_agreement:.0%}  "
        f"MAE={calibration.mean_absolute_error:.2f}  "
        f"pearson_r={r_str}  "
        f"n={len(calibration.cases)}"
    )
    for case in calibration.mismatches:
        print(
            f"  MISMATCH [{case.category}] human={case.human_score:.1f} "
            f"judge={case.judge_score:.2f}: {case.input!r}"
        )
        if case.reason:
            print(f"    judge reason: {case.reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--model", default=None, help="Override LEG_JUDGE_MODEL for this run")
    parser.add_argument("--min-agreement", type=float, default=0.8)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary")
    args = parser.parse_args(argv)

    model = judge_model(model_name=args.model)
    faithfulness = load_and_calibrate(
        args.dataset,
        faithfulness_metric(threshold=PASS_THRESHOLD_DEFAULT, model=model),
        "human_faithfulness",
        requires_context=True,
    )
    relevancy = load_and_calibrate(
        args.dataset,
        answer_relevancy_metric(threshold=PASS_THRESHOLD_DEFAULT, model=model),
        "human_relevancy",
    )

    if args.json:
        print(
            json.dumps(
                {
                    "model": model.get_model_name(),
                    "faithfulness": {
                        "agreement": faithfulness.pass_fail_agreement,
                        "mae": faithfulness.mean_absolute_error,
                        "pearson_r": faithfulness.pearson_r,
                        "n": len(faithfulness.cases),
                    },
                    "answer_relevancy": {
                        "agreement": relevancy.pass_fail_agreement,
                        "mae": relevancy.mean_absolute_error,
                        "pearson_r": relevancy.pearson_r,
                        "n": len(relevancy.cases),
                    },
                },
                indent=2,
            )
        )
    else:
        print(f"Judge model: {model.get_model_name()}\n")
        _print_report(faithfulness)
        print()
        _print_report(relevancy)

    below_threshold = [
        c for c in (faithfulness, relevancy) if c.pass_fail_agreement < args.min_agreement
    ]
    if below_threshold:
        names = ", ".join(c.metric_name for c in below_threshold)
        print(
            f"\nFAILED: {names} agreement below --min-agreement={args.min_agreement:.0%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
