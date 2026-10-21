"""Rule-based retrieval check: did the retrieved context contain the facts the answer needs?

Why a deterministic check next to the judge metrics: a retrieval regression (wrong chunks,
fewer chunks) is visible before any generation happens, so it can gate CI exactly — no judge
noise — while faithfulness/relevancy show its downstream effect on the answer.
"""

from __future__ import annotations

from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult


class ContextRecallMetric(Metric):
    """Score = fraction of `case.metadata["context_markers"]` found (case-insensitively) in
    `case.retrieval_context`. A case with no markers (e.g. an unanswerable question) passes."""

    def __init__(self, threshold: float = 1.0) -> None:
        super().__init__(threshold=threshold)

    @property
    def name(self) -> str:
        return "context_recall"

    def evaluate(self, case: EvalCase) -> MetricResult:
        markers: list[str] = case.metadata.get("context_markers") or []
        if not markers:
            return MetricResult(metric_name=self.name, score=1.0, passed=True, reason=None)
        context = " ".join(case.retrieval_context or []).lower()
        missing = [m for m in markers if m.lower() not in context]
        score = 1 - len(missing) / len(markers)
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            reason=f"retrieved context is missing: {missing}" if missing else None,
        )
