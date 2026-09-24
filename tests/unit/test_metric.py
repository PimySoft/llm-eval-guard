import pytest

from llm_eval_guard.core import EvalCase, Metric, MetricResult


class FakeMetric(Metric):
    """Minimal concrete Metric: scores 1.0 if actual_output contains expected_output."""

    @property
    def name(self) -> str:
        return "fake"

    def evaluate(self, case: EvalCase) -> MetricResult:
        score = 1.0 if (case.expected_output or "") in case.actual_output else 0.0
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            reason=None,
        )


def test_metric_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        Metric()  # type: ignore[abstract]


def test_fake_metric_passes_on_matching_output() -> None:
    metric = FakeMetric(threshold=0.5)
    case = EvalCase(input="What is 2+2?", actual_output="The answer is 4.", expected_output="4")

    result = metric.evaluate(case)

    assert result.metric_name == "fake"
    assert result.score == 1.0
    assert result.passed is True


def test_fake_metric_fails_below_threshold() -> None:
    metric = FakeMetric(threshold=0.5)
    case = EvalCase(input="What is 2+2?", actual_output="I don't know.", expected_output="4")

    result = metric.evaluate(case)

    assert result.score == 0.0
    assert result.passed is False


def test_eval_case_defaults() -> None:
    case = EvalCase(input="hi", actual_output="hello")

    assert case.expected_output is None
    assert case.retrieval_context is None
    assert case.metadata == {}
