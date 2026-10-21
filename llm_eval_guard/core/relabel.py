"""Labeler self-agreement: re-label a blind sample of golden cases and compare to the originals.

Why this exists: the human labels are the ground truth judge calibration measures against, so
their own consistency caps how good any judge can look (see docs/datasets.md).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from llm_eval_guard.core.calibration import PASS_THRESHOLD
from llm_eval_guard.core.models import EvalCase

LABEL_KEYS = ("human_faithfulness", "human_relevancy")


def blind_sample(cases: list[EvalCase], fraction: float, seed: int) -> list[dict[str, Any]]:
    """Pick ``fraction`` of ``cases`` at random and strip everything that hints at the original
    label (``expected_output``, ``note``, ``failure_mode``, the labels themselves).
    """
    k = max(1, round(len(cases) * fraction))
    picked = random.Random(seed).sample(cases, k)
    return [
        {
            "id": case.metadata["id"],
            "input": case.input,
            "actual_output": case.actual_output,
            "retrieval_context": case.retrieval_context,
            **dict.fromkeys(LABEL_KEYS),
        }
        for case in picked
    ]


@dataclass
class LabelAgreement:
    label_key: str
    n: int
    pass_fail_agreement: float
    exact_agreement: float
    mean_absolute_error: float


def self_agreement(
    original: list[EvalCase], relabeled: list[dict[str, Any]]
) -> list[LabelAgreement]:
    """Compare re-labeled records (matched by ``id``) against the original labels, per label key.

    Raises ``ValueError`` on an unknown id or an unfilled label, so a half-finished re-label pass
    can't silently report a number.
    """
    by_id = {case.metadata["id"]: case for case in original}
    pairs: dict[str, list[tuple[float, float]]] = {key: [] for key in LABEL_KEYS}
    for record in relabeled:
        case = by_id.get(record["id"])
        if case is None:
            raise ValueError(f"unknown case id {record['id']!r}")
        for key in LABEL_KEYS:
            if record.get(key) is None:
                raise ValueError(f"{record['id']}: {key} not filled in")
            pairs[key].append((float(case.metadata[key]), float(record[key])))

    results = []
    for key, scores in pairs.items():
        n = len(scores)
        if n == 0:
            raise ValueError("no re-labeled records")
        results.append(
            LabelAgreement(
                label_key=key,
                n=n,
                pass_fail_agreement=sum(
                    (a >= PASS_THRESHOLD) == (b >= PASS_THRESHOLD) for a, b in scores
                )
                / n,
                exact_agreement=sum(a == b for a, b in scores) / n,
                mean_absolute_error=sum(abs(a - b) for a, b in scores) / n,
            )
        )
    return results
