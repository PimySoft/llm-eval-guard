"""Judge calibration: measures how well an LLM-judge metric agrees with human-labeled scores.

Why this exists: an LLM judge is itself an unverified component until it's checked against
ground truth — wiring FaithfulnessMetric up to Ollama proves the *plumbing* works, not that its
scores are trustworthy. This module is what turns "the judge said 0.9" into a number you can
actually defend (see docs/judge-calibration.md).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from llm_eval_guard.core.dataset import load_golden_dataset
from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase

# A human/judge score at or above this counts as a "pass", purely for computing pass/fail
# agreement — independent of whatever threshold a metric is actually deployed with in CI.
PASS_THRESHOLD = 0.5

# Fixed seed so two runs over the same judge scores report the same interval.
BOOTSTRAP_SEED = 0
BOOTSTRAP_RESAMPLES = 2000


@dataclass
class CaseComparison:
    input: str
    category: str | None
    human_score: float
    judge_score: float
    reason: str | None
    failure_mode: str | None = None
    seconds: float = 0.0
    # Only the judge's cutoff is tunable; the human cutoff is fixed by what the labels mean.
    judge_threshold: float = PASS_THRESHOLD

    @property
    def human_pass(self) -> bool:
        return self.human_score >= PASS_THRESHOLD

    @property
    def judge_pass(self) -> bool:
        return self.judge_score >= self.judge_threshold

    @property
    def agrees(self) -> bool:
        return self.human_pass == self.judge_pass


@dataclass
class MetricCalibration:
    metric_name: str
    cases: list[CaseComparison] = field(default_factory=list)

    @property
    def pass_fail_agreement(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.agrees) / len(self.cases)

    @property
    def mean_absolute_error(self) -> float:
        if not self.cases:
            return 0.0
        return sum(abs(c.human_score - c.judge_score) for c in self.cases) / len(self.cases)

    @property
    def pearson_r(self) -> float | None:
        return _pearson(
            [c.human_score for c in self.cases],
            [c.judge_score for c in self.cases],
        )

    @property
    def mismatches(self) -> list[CaseComparison]:
        return [c for c in self.cases if not c.agrees]

    @property
    def mean_seconds(self) -> float:
        if not self.cases:
            return 0.0
        return sum(c.seconds for c in self.cases) / len(self.cases)

    def per_failure_mode(self) -> dict[str, tuple[float, int]]:
        """Agreement and case count per ``failure_mode`` tag (untagged cases group as "none")."""
        groups: dict[str, list[CaseComparison]] = {}
        for case in self.cases:
            groups.setdefault(case.failure_mode or "none", []).append(case)
        return {
            mode: (sum(1 for c in group if c.agrees) / len(group), len(group))
            for mode, group in sorted(groups.items())
        }

    def agreement_ci(
        self,
        confidence: float = 0.95,
        resamples: int = BOOTSTRAP_RESAMPLES,
        seed: int = BOOTSTRAP_SEED,
    ) -> tuple[float, float] | None:
        """Percentile-bootstrap confidence interval on pass/fail agreement.

        Why: at n≈40, one flipped case moves agreement by ~2.5 points — the interval shows when a
        gap between two judges is just resampling noise.
        """
        n = len(self.cases)
        if n == 0:
            return None
        hits = [1 if c.agrees else 0 for c in self.cases]
        rng = random.Random(seed)
        stats = sorted(sum(rng.choices(hits, k=n)) / n for _ in range(resamples))
        tail = (1 - confidence) / 2
        low = stats[int(tail * (resamples - 1))]
        high = stats[int((1 - tail) * (resamples - 1))]
        return low, high


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Hand-rolled Pearson correlation — no need to pull in scipy/numpy for one formula."""
    n = len(xs)
    if n < 2:
        return None
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return float(cov / (var_x**0.5 * var_y**0.5))


def calibrate(
    cases: list[EvalCase],
    metric: Metric,
    human_label_key: str,
    *,
    requires_context: bool = False,
    judge_threshold: float = PASS_THRESHOLD,
) -> MetricCalibration:
    """Score every case that carries ``human_label_key`` in its metadata with ``metric``, and
    compare against that human label. Cases missing the label (or missing retrieval_context when
    ``requires_context`` is set) are skipped — not every case in a golden set has to speak to
    every metric.
    """
    calibration = MetricCalibration(metric_name=metric.name)
    for case in cases:
        if human_label_key not in case.metadata:
            continue
        if requires_context and not case.retrieval_context:
            continue
        start = time.perf_counter()
        result = metric.evaluate(case)
        elapsed = time.perf_counter() - start
        calibration.cases.append(
            CaseComparison(
                input=case.input,
                category=case.metadata.get("category"),
                human_score=float(case.metadata[human_label_key]),
                judge_score=result.score,
                reason=result.reason,
                failure_mode=case.metadata.get("failure_mode"),
                seconds=elapsed,
                judge_threshold=judge_threshold,
            )
        )
    return calibration


def load_and_calibrate(
    dataset_path: str | Path,
    metric: Metric,
    human_label_key: str,
    *,
    requires_context: bool = False,
    split: str | None = None,
    judge_threshold: float = PASS_THRESHOLD,
) -> MetricCalibration:
    """``split`` keeps only cases whose ``metadata["split"]`` matches (``None`` = all cases)."""
    cases = load_golden_dataset(dataset_path)
    if split is not None:
        cases = [c for c in cases if c.metadata.get("split") == split]
    return calibrate(
        cases,
        metric,
        human_label_key,
        requires_context=requires_context,
        judge_threshold=judge_threshold,
    )
