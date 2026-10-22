"""Label agreement: re-label a blind sample of golden cases and compare any two label sets.

Two uses, same code: self-agreement (the original labeler again, days later) and inter-rater
agreement (a second labeler working only from docs/labeling-guide.md).

Why this exists: the human labels are the ground truth judge calibration measures against, so
their own consistency caps how good any judge can look (see docs/datasets.md).
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from llm_eval_guard.core.calibration import PASS_THRESHOLD, cohen_kappa
from llm_eval_guard.core.models import EvalCase

LABEL_KEYS = ("human_faithfulness", "human_relevancy")

# Who labeled the shipped dataset; the name `score` compares a re-label pass against.
ORIGINAL_LABELER = "original"

LabelSet = dict[str, dict[str, float]]
"""Case id -> {label key -> score}."""


def blind_sample(
    cases: list[EvalCase],
    fraction: float,
    seed: int,
    labeler: str,
    exclude: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Pick at least ``fraction`` of ``cases`` at random and strip everything that hints at the
    original label (``expected_output``, ``note``, ``failure_mode``, the labels themselves).

    The same ``seed`` gives every labeler the same cases, so their label sets can be compared.
    ``exclude`` drops ids from the pool (e.g. cases the labeling guide was revised on); the sample
    size is still ``fraction`` of all cases.
    """
    k = max(1, math.ceil(len(cases) * fraction))
    pool = [case for case in cases if case.metadata["id"] not in exclude]
    if len(pool) < k:
        raise ValueError(f"only {len(pool)} cases left after exclusions, need {k}")
    picked = random.Random(seed).sample(pool, k)
    return [
        {
            "id": case.metadata["id"],
            "labeler": labeler,
            "input": case.input,
            "actual_output": case.actual_output,
            "retrieval_context": case.retrieval_context,
            **dict.fromkeys(LABEL_KEYS),
        }
        for case in picked
    ]


def labels_from_cases(cases: Iterable[EvalCase]) -> LabelSet:
    """The original labels shipped in the golden dataset, as a ``LabelSet``."""
    return {
        case.metadata["id"]: {key: float(case.metadata[key]) for key in LABEL_KEYS}
        for case in cases
    }


def labels_from_records(records: Iterable[Mapping[str, Any]]) -> LabelSet:
    """Labels from filled-in ``blind_sample`` records.

    Raises ``ValueError`` on an unfilled label or a repeated id, so a half-finished re-label pass
    can't silently report a number.
    """
    labels: LabelSet = {}
    for record in records:
        case_id = record["id"]
        if case_id in labels:
            raise ValueError(f"duplicate case id {case_id!r}")
        for key in LABEL_KEYS:
            if record.get(key) is None:
                raise ValueError(f"{case_id}: {key} not filled in")
        labels[case_id] = {key: float(record[key]) for key in LABEL_KEYS}
    return labels


@dataclass
class LabelAgreement:
    label_key: str
    n: int
    pass_fail_agreement: float
    exact_agreement: float
    mean_absolute_error: float
    # None when kappa is undefined (both label sets constant and identical).
    pass_fail_kappa: float | None
    # Ids whose scores differ at all, sorted; the cases to discuss when fixing the guide.
    disagreements: list[str] = field(default_factory=list)


def compare_labels(reference: LabelSet, other: LabelSet) -> list[LabelAgreement]:
    """Agreement per label key between two label sets, over the ids in ``other``.

    ``reference`` may cover more cases (e.g. the full dataset vs a 20% sample); an id in
    ``other`` that ``reference`` lacks raises ``ValueError``.
    """
    if not other:
        raise ValueError("no labeled records to compare")
    for case_id in other:
        if case_id not in reference:
            raise ValueError(f"unknown case id {case_id!r}")

    ids = sorted(other)
    results = []
    for key in LABEL_KEYS:
        a = [reference[i][key] for i in ids]
        b = [other[i][key] for i in ids]
        n = len(ids)
        results.append(
            LabelAgreement(
                label_key=key,
                n=n,
                pass_fail_agreement=sum(
                    (x >= PASS_THRESHOLD) == (y >= PASS_THRESHOLD)
                    for x, y in zip(a, b, strict=True)
                )
                / n,
                exact_agreement=sum(x == y for x, y in zip(a, b, strict=True)) / n,
                mean_absolute_error=sum(abs(x - y) for x, y in zip(a, b, strict=True)) / n,
                pass_fail_kappa=cohen_kappa(
                    [x >= PASS_THRESHOLD for x in a], [y >= PASS_THRESHOLD for y in b]
                ),
                disagreements=[i for i, x, y in zip(ids, a, b, strict=True) if x != y],
            )
        )
    return results


def self_agreement(
    original: list[EvalCase], relabeled: list[dict[str, Any]]
) -> list[LabelAgreement]:
    """Compare re-labeled records (matched by ``id``) against the original labels."""
    return compare_labels(labels_from_cases(original), labels_from_records(relabeled))
