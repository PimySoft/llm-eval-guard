"""The engine-agnostic scoring interface every metric backend implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from llm_eval_guard.core.models import EvalCase, MetricResult


class Metric(ABC):
    """Common interface for anything that scores an :class:`EvalCase`.

    Why: the runner, reporting, and CI threshold-gating code (Phase 3+) only ever talk to this
    interface, never to DeepEval/Ragas/regex checks directly. That's what lets Phase 2.3 (Ragas),
    Phase 4 (security heuristics), and any future engine plug in without touching the runner.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used in reports, CLI output, and ``leg.config.yaml`` keys."""

    @abstractmethod
    def evaluate(self, case: EvalCase) -> MetricResult:
        """Score a single case and return a normalized result."""
