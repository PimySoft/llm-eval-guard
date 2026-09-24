import pytest

from llm_eval_guard.core.calibration import calibrate
from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult


class PerfectJudge(Metric):
    """Always agrees with the human label exactly — a sanity-check fixture for calibrate()."""

    @property
    def name(self) -> str:
        return "perfect"

    def evaluate(self, case: EvalCase) -> MetricResult:
        score = case.metadata["human_score"]
        return MetricResult(metric_name=self.name, score=score, passed=score >= 0.5, reason=None)


class OppositeJudge(Metric):
    """Always disagrees with the human label — worst-case fixture."""

    @property
    def name(self) -> str:
        return "opposite"

    def evaluate(self, case: EvalCase) -> MetricResult:
        score = 1.0 - case.metadata["human_score"]
        return MetricResult(metric_name=self.name, score=score, passed=score >= 0.5, reason=None)


def _cases() -> list[EvalCase]:
    return [
        EvalCase(input="a", actual_output="x", metadata={"human_score": 1.0}),
        EvalCase(input="b", actual_output="y", metadata={"human_score": 0.0}),
        EvalCase(input="c", actual_output="z", metadata={"human_score": 1.0}),
        EvalCase(input="d", actual_output="w", metadata={}),  # no label -> skipped
    ]


def test_calibrate_perfect_judge_has_full_agreement() -> None:
    calibration = calibrate(_cases(), PerfectJudge(), "human_score")

    assert len(calibration.cases) == 3  # the unlabeled case is skipped
    assert calibration.pass_fail_agreement == 1.0
    assert calibration.mean_absolute_error == 0.0
    assert calibration.pearson_r == pytest.approx(1.0)
    assert calibration.mismatches == []


def test_calibrate_opposite_judge_has_zero_agreement() -> None:
    calibration = calibrate(_cases(), OppositeJudge(), "human_score")

    assert calibration.pass_fail_agreement == 0.0
    assert calibration.mean_absolute_error == 1.0
    assert len(calibration.mismatches) == 3


def test_calibrate_skips_cases_missing_retrieval_context_when_required() -> None:
    cases = [
        EvalCase(
            input="a",
            actual_output="x",
            metadata={"human_score": 1.0},
            retrieval_context=["ctx"],
        ),
        EvalCase(input="b", actual_output="y", metadata={"human_score": 1.0}),  # no context
    ]

    calibration = calibrate(cases, PerfectJudge(), "human_score", requires_context=True)

    assert len(calibration.cases) == 1


def test_empty_calibration_has_zero_agreement_not_a_crash() -> None:
    calibration = calibrate([], PerfectJudge(), "human_score")

    assert calibration.pass_fail_agreement == 0.0
    assert calibration.mean_absolute_error == 0.0
    assert calibration.pearson_r is None
