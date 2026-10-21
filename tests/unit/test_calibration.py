import json

import pytest

from llm_eval_guard.core.calibration import calibrate, load_and_calibrate
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


def test_per_failure_mode_groups_agreement_by_tag() -> None:
    cases = [
        EvalCase(input="a", actual_output="x", metadata={"human_score": 1.0}),
        EvalCase(
            input="b",
            actual_output="y",
            metadata={"human_score": 0.0, "failure_mode": "hallucinated-detail"},
        ),
    ]

    calibration = calibrate(cases, PerfectJudge(), "human_score")

    assert calibration.per_failure_mode() == {"hallucinated-detail": (1.0, 1), "none": (1.0, 1)}


def test_agreement_ci_brackets_the_point_estimate_and_is_deterministic() -> None:
    cases = [
        EvalCase(input=str(i), actual_output="x", metadata={"human_score": float(i % 2)})
        for i in range(40)
    ]
    # Half the cases disagree: flip the label only on the first 10.
    calibration = calibrate(cases, PerfectJudge(), "human_score")
    for case in calibration.cases[:10]:
        case.judge_score = 1.0 - case.human_score

    ci = calibration.agreement_ci()

    assert ci is not None
    low, high = ci
    assert low < calibration.pass_fail_agreement < high
    assert ci == calibration.agreement_ci()


def test_agreement_ci_is_none_for_empty_calibration() -> None:
    assert calibrate([], PerfectJudge(), "human_score").agreement_ci() is None


def test_load_and_calibrate_filters_by_split(tmp_path) -> None:
    rows = [
        {"input": "a", "actual_output": "x", "metadata": {"human_score": 1.0, "split": "dev"}},
        {"input": "b", "actual_output": "y", "metadata": {"human_score": 1.0, "split": "test"}},
    ]
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))

    calibration = load_and_calibrate(path, PerfectJudge(), "human_score", split="dev")

    assert [c.input for c in calibration.cases] == ["a"]
