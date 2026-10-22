#!/usr/bin/env python
"""Calibrates the local Ollama judge model against the human labels in the golden dataset.

Run this whenever the judge model or prompt changes (e.g. swapping llama3.2:1b for phi3:mini) —
model choice is a tuning decision backed by this number, not a guess. See docs/judge-calibration.md.

Usage:
    python scripts/calibrate_judge.py --split dev
    python scripts/calibrate_judge.py --model phi3:mini --split dev --min-agreement 0.8
    python scripts/calibrate_judge.py --json > calibration_result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from llm_eval_guard.core.calibration import PASS_THRESHOLD, MetricCalibration, load_and_calibrate
from llm_eval_guard.metrics.deepeval_adapter import (
    PASS_THRESHOLD_DEFAULT,
    answer_relevancy_metric,
    faithfulness_metric,
    judge_model,
)

DEFAULT_DATASET = Path(__file__).parent.parent / "datasets" / "golden" / "sample_rag_qa.jsonl"


def _summary(calibration: MetricCalibration, judge_threshold: float) -> dict[str, Any]:
    ci = calibration.agreement_ci()
    return {
        "judge_threshold": judge_threshold,
        "agreement": calibration.pass_fail_agreement,
        "agreement_ci95": list(ci) if ci else None,
        "kappa": calibration.pass_fail_kappa,
        "mae": calibration.mean_absolute_error,
        "pearson_r": calibration.pearson_r,
        "seconds_per_case": calibration.mean_seconds,
        "n": len(calibration.cases),
        "per_failure_mode": {
            mode: {"agreement": agreement, "n": n}
            for mode, (agreement, n) in calibration.per_failure_mode().items()
        },
        "cases": [
            {
                "input": c.input,
                "failure_mode": c.failure_mode,
                "human_score": c.human_score,
                "judge_score": c.judge_score,
                "seconds": c.seconds,
            }
            for c in calibration.cases
        ],
    }


def _print_report(calibration: MetricCalibration) -> None:
    r = calibration.pearson_r
    r_str = "n/a" if r is None else f"{r:.2f}"
    ci = calibration.agreement_ci()
    ci_str = "n/a" if ci is None else f"[{ci[0]:.0%}, {ci[1]:.0%}]"
    kappa = calibration.pass_fail_kappa
    kappa_str = "n/a" if kappa is None else f"{kappa:.2f}"
    print(
        f"{calibration.metric_name}: "
        f"agreement={calibration.pass_fail_agreement:.0%} (95% CI {ci_str})  "
        f"kappa={kappa_str}  "
        f"MAE={calibration.mean_absolute_error:.2f}  "
        f"pearson_r={r_str}  "
        f"s/case={calibration.mean_seconds:.1f}  "
        f"n={len(calibration.cases)}"
    )
    for mode, (agreement, n) in calibration.per_failure_mode().items():
        print(f"  {mode}: {agreement:.0%} (n={n})")
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
    parser.add_argument(
        "--split",
        choices=["dev", "test"],
        default=None,
        help="Only score this split (default: all cases). Tune on dev; report test once.",
    )
    parser.add_argument("--min-agreement", type=float, default=0.8)
    # Per metric because the judges err in opposite directions: faithfulness over-credits
    # half-supported answers, relevancy under-scores good ones (docs/judge-calibration.md).
    parser.add_argument(
        "--faithfulness-threshold",
        type=float,
        default=PASS_THRESHOLD,
        help="Judge faithfulness score counted as a pass (human labels always pass at 0.5). "
        "Tune on dev only.",
    )
    parser.add_argument(
        "--relevancy-threshold",
        type=float,
        default=PASS_THRESHOLD,
        help="Judge answer_relevancy score counted as a pass. Tune on dev only.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary")
    args = parser.parse_args(argv)

    model = judge_model(model_name=args.model)
    faithfulness = load_and_calibrate(
        args.dataset,
        faithfulness_metric(threshold=PASS_THRESHOLD_DEFAULT, model=model),
        "human_faithfulness",
        requires_context=True,
        split=args.split,
        judge_threshold=args.faithfulness_threshold,
    )
    relevancy = load_and_calibrate(
        args.dataset,
        answer_relevancy_metric(threshold=PASS_THRESHOLD_DEFAULT, model=model),
        "human_relevancy",
        split=args.split,
        judge_threshold=args.relevancy_threshold,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "model": model.get_model_name(),
                    "split": args.split or "all",
                    "faithfulness": _summary(faithfulness, args.faithfulness_threshold),
                    "answer_relevancy": _summary(relevancy, args.relevancy_threshold),
                },
                indent=2,
            )
        )
    else:
        print(
            f"Judge model: {model.get_model_name()}  split: {args.split or 'all'}  "
            f"judge thresholds: faithfulness={args.faithfulness_threshold} "
            f"answer_relevancy={args.relevancy_threshold}\n"
        )
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
