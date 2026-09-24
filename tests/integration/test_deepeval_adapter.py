"""Tests the DeepEval adapter's normalization logic with the judge LLM stubbed out.

Why stub at the DeepEval-metric boundary rather than the LLM's raw JSON responses: DeepEval's
FaithfulnessMetric alone makes four separate structured LLM calls per case (truths, claims,
verdicts, reason), each with its own pydantic schema — hand-simulating that whole chain would
mostly test DeepEval's internals, not ours, and would break on any DeepEval refactor. What we
own and need to verify is the mapping from a scored DeepEval metric to our MetricResult; the
`live_llm`-marked tests below separately prove the real Ollama wiring works end to end.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from deepeval.models import DeepEvalBaseLLM

from llm_eval_guard.core import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import (
    DeepEvalMetric,
    answer_relevancy_metric,
    faithfulness_metric,
    judge_model,
)


def _stubbed_deepeval_metric(score: float, threshold: float, reason: str | None) -> MagicMock:
    stub = MagicMock()
    stub.threshold = threshold
    stub.score = score
    stub.reason = reason
    stub.is_successful.return_value = score >= threshold
    return stub


def test_evaluate_maps_passing_deepeval_result() -> None:
    stub = _stubbed_deepeval_metric(score=0.92, threshold=0.8, reason="Fully grounded.")
    metric = DeepEvalMetric(stub, name="faithfulness")
    case = EvalCase(input="q", actual_output="a", retrieval_context=["ctx"])

    result = metric.evaluate(case)

    stub.measure.assert_called_once()
    assert result.metric_name == "faithfulness"
    assert result.score == 0.92
    assert result.passed is True
    assert result.reason == "Fully grounded."


def test_evaluate_maps_failing_deepeval_result() -> None:
    stub = _stubbed_deepeval_metric(score=0.3, threshold=0.8, reason="Unsupported claim found.")
    metric = DeepEvalMetric(stub, name="faithfulness")
    case = EvalCase(input="q", actual_output="a", retrieval_context=["ctx"])

    result = metric.evaluate(case)

    assert result.passed is False
    assert result.score == 0.3


def test_evaluate_treats_none_score_as_zero() -> None:
    stub = _stubbed_deepeval_metric(score=0.0, threshold=0.5, reason=None)
    stub.score = None
    stub.is_successful.return_value = False
    metric = DeepEvalMetric(stub, name="faithfulness")
    case = EvalCase(input="q", actual_output="a")

    result = metric.evaluate(case)

    assert result.score == 0.0
    assert result.passed is False


def test_deepeval_metric_threshold_none_defaults_to_half() -> None:
    stub = _stubbed_deepeval_metric(score=0.6, threshold=0.5, reason=None)
    stub.threshold = None

    metric = DeepEvalMetric(stub, name="faithfulness")

    assert metric.threshold == 0.5


def test_judge_model_reads_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEG_JUDGE_MODEL", "phi3:mini")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example-host:11434")

    model = judge_model()

    assert model.name == "phi3:mini"
    assert model.base_url == "http://example-host:11434"


def test_judge_model_explicit_args_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEG_JUDGE_MODEL", "phi3:mini")

    model = judge_model(model_name="llama3.2:1b")

    assert model.name == "llama3.2:1b"


def test_faithfulness_metric_never_defaults_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guards the $0 cost policy: constructing a metric without an explicit model must still
    resolve to the local Ollama judge, never DeepEval's default (paid) OpenAI model."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LEG_JUDGE_MODEL", raising=False)

    metric = faithfulness_metric(threshold=0.8)

    assert metric._metric.model is not None
    assert metric._metric.model.get_model_name() == "qwen2.5:0.5b (Ollama)"


def test_answer_relevancy_metric_uses_provided_model() -> None:
    stub_model = MagicMock(spec=DeepEvalBaseLLM)
    stub_model.get_model_name.return_value = "stub-model"

    metric = answer_relevancy_metric(threshold=0.7, model=stub_model)

    assert metric._metric.model is stub_model
    assert metric.threshold == 0.7
