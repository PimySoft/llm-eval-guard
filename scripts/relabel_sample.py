#!/usr/bin/env python
"""Measures human label agreement on the golden dataset. See docs/datasets.md.

Usage:
    python scripts/relabel_sample.py sample                    # blind 20% sample, for you
    # ...days later, fill in human_faithfulness/human_relevancy without opening the dataset...
    python scripts/relabel_sample.py score                     # self-agreement vs the originals

    python scripts/relabel_sample.py sample --labeler alex     # same cases, for a second labeler
    python scripts/relabel_sample.py score --labeler alex      # alex vs the originals
    python scripts/relabel_sample.py compare A.jsonl B.jsonl   # any two filled-in label files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from llm_eval_guard.core.dataset import load_golden_dataset
from llm_eval_guard.core.relabel import (
    ORIGINAL_LABELER,
    LabelAgreement,
    blind_sample,
    compare_labels,
    labels_from_cases,
    labels_from_records,
)

GOLDEN = Path(__file__).parent.parent / "datasets" / "golden"
DEFAULT_DATASET = GOLDEN / "sample_rag_qa.jsonl"
SELF_LABELER = "self"


def _relabel_file(labeler: str) -> Path:
    # The self-agreement file keeps its Phase 7 name; other labelers get their own file.
    suffix = "" if labeler == SELF_LABELER else f".{labeler}"
    return GOLDEN / f"sample_rag_qa.relabel{suffix}.jsonl"


def _read_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _print_agreement(results: list[LabelAgreement], a: str, b: str) -> None:
    print(f"{a} vs {b}")
    for result in results:
        kappa = "n/a" if result.pass_fail_kappa is None else f"{result.pass_fail_kappa:.2f}"
        print(
            f"{result.label_key}: pass/fail agreement={result.pass_fail_agreement:.0%}  "
            f"kappa={kappa}  exact={result.exact_agreement:.0%}  "
            f"MAE={result.mean_absolute_error:.2f}  n={result.n}"
        )
        if result.disagreements:
            print(f"  differ on: {', '.join(result.disagreements)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("sample", "score"):
        cmd = sub.add_parser(name)
        cmd.add_argument(
            "--labeler",
            default=SELF_LABELER,
            help=f"Who labels this pass (default: {SELF_LABELER!r}, the original labeler)",
        )
        cmd.add_argument("--relabel-file", type=Path, default=None)
        if name == "sample":
            cmd.add_argument("--fraction", type=float, default=0.2)
            cmd.add_argument("--seed", type=int, default=2026)

    compare = sub.add_parser("compare")
    compare.add_argument("file_a", type=Path)
    compare.add_argument("file_b", type=Path)

    args = parser.parse_args(argv)

    if args.command == "compare":
        a_records, b_records = _read_records(args.file_a), _read_records(args.file_b)
        results = compare_labels(labels_from_records(a_records), labels_from_records(b_records))
        _print_agreement(
            results, a_records[0].get("labeler", "A"), b_records[0].get("labeler", "B")
        )
        return 0

    cases = load_golden_dataset(args.dataset)
    relabel_file = args.relabel_file or _relabel_file(args.labeler)

    if args.command == "sample":
        if relabel_file.exists():
            print(f"{relabel_file} already exists — not overwriting", file=sys.stderr)
            return 1
        records = blind_sample(cases, args.fraction, args.seed, args.labeler)
        relabel_file.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
        )
        print(f"Wrote {len(records)} blind cases to {relabel_file}")
        return 0

    results = compare_labels(
        labels_from_cases(cases), labels_from_records(_read_records(relabel_file))
    )
    _print_agreement(results, ORIGINAL_LABELER, args.labeler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
