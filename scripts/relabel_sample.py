#!/usr/bin/env python
"""Measures labeler self-agreement on the golden dataset. See docs/datasets.md.

Usage:
    python scripts/relabel_sample.py sample              # writes a blind 20% sample to label
    # ...days later, fill in human_faithfulness/human_relevancy without opening the dataset...
    python scripts/relabel_sample.py score               # compares against the original labels
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from llm_eval_guard.core.dataset import load_golden_dataset
from llm_eval_guard.core.relabel import blind_sample, self_agreement

GOLDEN = Path(__file__).parent.parent / "datasets" / "golden"
DEFAULT_DATASET = GOLDEN / "sample_rag_qa.jsonl"
DEFAULT_RELABEL = GOLDEN / "sample_rag_qa.relabel.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sample", "score"])
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--relabel-file", type=Path, default=DEFAULT_RELABEL)
    parser.add_argument("--fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    cases = load_golden_dataset(args.dataset)

    if args.command == "sample":
        if args.relabel_file.exists():
            print(f"{args.relabel_file} already exists — not overwriting", file=sys.stderr)
            return 1
        records = blind_sample(cases, args.fraction, args.seed)
        args.relabel_file.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
        )
        print(f"Wrote {len(records)} blind cases to {args.relabel_file}")
        return 0

    relabeled = [
        json.loads(line)
        for line in args.relabel_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for result in self_agreement(cases, relabeled):
        print(
            f"{result.label_key}: pass/fail agreement={result.pass_fail_agreement:.0%}  "
            f"exact={result.exact_agreement:.0%}  MAE={result.mean_absolute_error:.2f}  "
            f"n={result.n}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
