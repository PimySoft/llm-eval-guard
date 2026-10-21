"""Runner error handling: a judge call that errors fails its case instead of the whole run."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_eval_guard.core import runner
from llm_eval_guard.core.cache import ResultCache
from llm_eval_guard.core.config import LegConfig
from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult


class _Exploding(Metric):
    @property
    def name(self) -> str:
        return "faithfulness"

    def evaluate(self, case: EvalCase) -> MetricResult:
        raise TimeoutError("call timed out after 88.5s")


def _config(tmp_path: Path, *, fast: bool) -> LegConfig:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text('{"input": "q", "actual_output": "a"}\n', encoding="utf-8")
    return LegConfig.model_validate(
        {
            "suites": {
                "s": {"dataset": str(dataset), "metrics": [{"name": "faithfulness", "fast": fast}]}
            }
        }
    )


@pytest.fixture(autouse=True)
def _exploding_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "build_metric", lambda cfg, judge: _Exploding())


def test_judge_error_becomes_a_failed_case(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path / "cache.json")

    result = runner.run_suite("s", _config(tmp_path, fast=False), cache=cache)

    (case_result,) = result.case_results
    assert not case_result.result.passed
    assert (case_result.result.reason or "").startswith("judge error: TimeoutError")
    cache.save()
    assert (
        ResultCache(tmp_path / "cache.json").get(
            "faithfulness", EvalCase(input="q", actual_output="a")
        )
        is None
    )


def test_rule_based_metric_errors_still_raise(tmp_path: Path) -> None:
    with pytest.raises(TimeoutError):
        runner.run_suite("s", _config(tmp_path, fast=True))
