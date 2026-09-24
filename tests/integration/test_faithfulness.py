"""Example end-to-end usage of the faithfulness metric against the golden dataset.

Why only the "should pass" cases are asserted here, not the whole dataset: this file is a
*regression suite* pattern demo (real answers should stay faithful), not the judge's accuracy
check — that's scripts/calibrate_judge.py / docs/judge-calibration.md, which is exactly where the
hallucination-labeled cases in the golden set get used.

Why a minimum pass *rate* rather than requiring every case to pass: the local judge model is
probabilistic — gating a regression suite on every single score would make it flaky by
construction, even with a well-calibrated judge.

Why `xfail`: scripts/calibrate_judge.py measured the *default* judge (qwen2.5:0.5b, chosen for
CPU-only CI speed — see metrics/deepeval_adapter.py) at 40% pass/fail agreement against human
labels, well under a usable bar. Asserting a meaningful MIN_PASS_RATE against a judge known to be
this unreliable would either be a flaky red build or a dishonestly low bar chosen just to pass.
`xfail(strict=False)` records that honestly: expected-to-fail with the shipped default, and
non-fatal (not reported as a failure) if you swap LEG_JUDGE_MODEL for a stronger judge and it
starts passing. See docs/judge-calibration.md.
"""

from __future__ import annotations

import pytest
from deepeval.models.llms import OllamaModel

from llm_eval_guard.core import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import faithfulness_metric
from llm_eval_guard.pytest_plugin import assert_min_pass_rate

MIN_PASS_RATE = 0.8

pytestmark = [
    pytest.mark.live_llm,
    # `eval_metric` is attached here purely as declarative metadata (`-m eval_metric` selects
    # this file) — the actual gate is assert_min_pass_rate() below, not assert_eval_metric(),
    # for the reasons in the module docstring.
    pytest.mark.eval_metric(name="faithfulness", threshold=MIN_PASS_RATE),
    pytest.mark.xfail(
        reason="Default judge (qwen2.5:0.5b) fails calibration — see docs/judge-calibration.md",
        strict=False,
    ),
]


def _known_faithful_cases(golden_dataset: list[EvalCase]) -> list[EvalCase]:
    return [c for c in golden_dataset if c.metadata.get("human_faithfulness") == 1.0]


def test_faithfulness_on_golden_set(golden_dataset: list[EvalCase], judge_llm: OllamaModel) -> None:
    metric = faithfulness_metric(threshold=0.5, model=judge_llm)
    known_faithful = _known_faithful_cases(golden_dataset)
    assert known_faithful, "golden dataset has no human_faithfulness==1.0 cases to regress on"

    results = [metric.evaluate(case) for case in known_faithful]

    assert_min_pass_rate(results, MIN_PASS_RATE)
