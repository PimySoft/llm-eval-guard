"""Example end-to-end usage of the faithfulness metric against the golden dataset.

Why only the "should pass" cases are asserted here, not the whole dataset: this file is a
*regression suite* pattern demo (real answers should stay faithful), not the judge's accuracy
check — that's scripts/calibrate_judge.py / docs/judge-calibration.md, which is exactly where the
hallucination-labeled cases in the golden set get used.

Why a minimum pass *rate* rather than requiring every case to pass: the local judge model is
probabilistic — gating a regression suite on every single score would make it flaky by
construction, even with a well-calibrated judge.

Why MIN_PASS_RATE is 0.7, not 0.8: the calibrated judge (qwen2.5:7b) agreed with the human
faithfulness labels 71% of the time on the held-out split — the gate can't honestly demand more
than the judge can deliver. Why the 0.6 metric threshold: it's the calibrated judge cutoff.
Under the CI smoke-check judge this is a strict xfail (tests/integration/_judge.py).
See docs/judge-calibration.md.
"""

from __future__ import annotations

import pytest
from deepeval.models.llms import OllamaModel

from llm_eval_guard.core import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import faithfulness_metric
from llm_eval_guard.pytest_plugin import assert_min_pass_rate
from tests.integration._judge import xfail_under_ci_judge

MIN_PASS_RATE = 0.7

pytestmark = [
    pytest.mark.live_llm,
    # `eval_metric` is attached here purely as declarative metadata (`-m eval_metric` selects
    # this file) — the actual gate is assert_min_pass_rate() below, not assert_eval_metric(),
    # for the reasons in the module docstring.
    pytest.mark.eval_metric(name="faithfulness", threshold=MIN_PASS_RATE),
    xfail_under_ci_judge,
]


def _known_faithful_cases(golden_dataset: list[EvalCase]) -> list[EvalCase]:
    return [c for c in golden_dataset if c.metadata.get("human_faithfulness") == 1.0]


def test_faithfulness_on_golden_set(golden_dataset: list[EvalCase], judge_llm: OllamaModel) -> None:
    metric = faithfulness_metric(threshold=0.6, model=judge_llm)
    known_faithful = _known_faithful_cases(golden_dataset)
    assert known_faithful, "golden dataset has no human_faithfulness==1.0 cases to regress on"

    results = [metric.evaluate(case) for case in known_faithful]

    assert_min_pass_rate(results, MIN_PASS_RATE)
