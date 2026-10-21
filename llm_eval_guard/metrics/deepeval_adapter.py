"""Adapts DeepEval's metrics to the internal :class:`Metric` interface.

Why Ollama, not ``OPENAI_API_KEY``: DeepEval's judge metrics need *some* LLM to grade
faithfulness/relevancy, and by default that's a paid OpenAI call. The $0 cost policy (see
plan.md) requires every judge call to hit a local model instead, so :func:`judge_model` builds
DeepEval's own :class:`~deepeval.models.llms.OllamaModel` — DeepEval already ships a correct,
schema-constrained ``DeepEvalBaseLLM`` wrapper for Ollama, so reimplementing one here would only
add a worse copy of code DeepEval already maintains. Never construct a metric with ``model=None``
in this module; that silently falls back to OpenAI.
"""

from __future__ import annotations

import os
from typing import Any, cast

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    FaithfulnessMetric,
    ToxicityMetric,
)
from deepeval.metrics.base_metric import BaseMetric as DeepEvalBaseMetric
from deepeval.models.llms import OllamaModel
from deepeval.test_case import LLMTestCase

from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult

# Confident AI (DeepEval's hosted dashboard) is opt-in telemetry/cloud sync we never want on by
# default — this only takes effect if the host process hasn't already set the var, so a
# contributor who explicitly opts in by exporting it themselves is still respected.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")

# Two judge roles (docs/judge-calibration.md):
# - DEFAULT_JUDGE_MODEL is the "recommended" judge — the best of six local models calibrated
#   against the human labels; use it for local/self-hosted gating.
# - CI_JUDGE_MODEL is a fast, uncalibrated smoke-check judge for free CPU-only Actions runners,
#   where a 7B judge is too slow. Its scores prove the plumbing runs, not that answers are good.
# Changing either requires re-running scripts/calibrate_judge.py first.
DEFAULT_JUDGE_MODEL = "qwen2.5:7b"
CI_JUDGE_MODEL = "qwen2.5:0.5b"

# A judge score at or above this counts as a "pass" for calibration purposes (scripts/
# calibrate_judge.py) — separate from whatever threshold a metric is actually deployed with.
PASS_THRESHOLD_DEFAULT = 0.5


def resolve_judge_model_name(model_name: str | None = None) -> str:
    """Explicit name, else ``LEG_JUDGE_MODEL``, else :data:`DEFAULT_JUDGE_MODEL`."""
    return model_name or os.environ.get("LEG_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)


def judge_model(model_name: str | None = None, base_url: str | None = None) -> OllamaModel:
    """Build the local Ollama judge model that DeepEval metrics score against.

    ``model_name``/``base_url`` fall back to ``LEG_JUDGE_MODEL``/``OLLAMA_BASE_URL`` env vars so
    CI and local dev can swap models without code changes (see docs/judge-calibration.md for why
    swapping models is a calibration decision, not a guess).
    """
    return OllamaModel(
        model=resolve_judge_model_name(model_name),
        base_url=base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    )


def _to_test_case(case: EvalCase) -> LLMTestCase:
    return LLMTestCase(
        input=case.input,
        actual_output=case.actual_output,
        expected_output=case.expected_output,
        # EvalCase only ever holds plain-text chunks; DeepEval's wider union also allows
        # multimodal RetrievedContextData, which this project doesn't use.
        retrieval_context=cast("list[str | Any] | None", case.retrieval_context),
    )


class DeepEvalMetric(Metric):
    """Wraps one DeepEval ``BaseMetric`` instance so the runner never imports DeepEval directly."""

    def __init__(self, deepeval_metric: DeepEvalBaseMetric, name: str) -> None:
        threshold = deepeval_metric.threshold
        if threshold is None:
            threshold = 0.5
        super().__init__(threshold=threshold)
        self._metric = deepeval_metric
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, case: EvalCase) -> MetricResult:
        test_case = _to_test_case(case)
        self._metric.measure(test_case, _show_indicator=False)
        return MetricResult(
            metric_name=self._name,
            score=self._metric.score if self._metric.score is not None else 0.0,
            passed=bool(self._metric.is_successful()),
            reason=self._metric.reason,
        )


def faithfulness_metric(threshold: float = 0.8, model: OllamaModel | None = None) -> DeepEvalMetric:
    """Does the answer avoid claims unsupported by the retrieved context?"""
    return DeepEvalMetric(
        FaithfulnessMetric(threshold=threshold, model=model or judge_model()),
        name="faithfulness",
    )


def answer_relevancy_metric(
    threshold: float = 0.8, model: OllamaModel | None = None
) -> DeepEvalMetric:
    """Does the answer actually address the input, independent of factual grounding?

    Why score this separately from faithfulness: an answer can be fully grounded in the
    retrieved context (faithful) while ignoring what the user asked (irrelevant), or vice versa —
    they catch different regressions (retrieval/generation drift vs. off-topic generation).
    """
    return DeepEvalMetric(
        AnswerRelevancyMetric(threshold=threshold, model=model or judge_model()),
        name="answer_relevancy",
    )


def contextual_precision_metric(
    threshold: float = 0.8, model: OllamaModel | None = None
) -> DeepEvalMetric:
    """Are the most relevant retrieved chunks ranked above the irrelevant ones?"""
    return DeepEvalMetric(
        ContextualPrecisionMetric(threshold=threshold, model=model or judge_model()),
        name="contextual_precision",
    )


def toxicity_metric(threshold: float = 0.5, model: OllamaModel | None = None) -> DeepEvalMetric:
    """Does the output contain toxic language (insults, threats, hate speech, profanity)?

    Why DeepEval's judge-based metric instead of a dedicated local classifier (e.g. Detoxify):
    it reuses the Ollama judge wiring this module already maintains for faithfulness/relevancy,
    at no extra dependency weight — pulling in a second, separately-maintained toxicity model
    would duplicate infrastructure this adapter already has for exactly this purpose. See
    plan.md Phase 4.3.
    """
    return DeepEvalMetric(
        ToxicityMetric(threshold=threshold, model=model or judge_model()),
        name="toxicity",
    )
