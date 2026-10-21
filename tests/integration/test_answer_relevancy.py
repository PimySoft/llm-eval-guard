"""Example end-to-end usage of the answer-relevancy metric against the golden dataset.

See test_faithfulness.py for why the gate is a minimum pass *rate* and why this suite is a strict
xfail only under the CI smoke-check judge. MIN_PASS_RATE stays 0.8: relevancy cleared it held-out.
"""

from __future__ import annotations

import pytest
from deepeval.models.llms import OllamaModel

from llm_eval_guard.core import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import answer_relevancy_metric
from llm_eval_guard.pytest_plugin import assert_min_pass_rate
from tests.integration._judge import xfail_under_ci_judge

MIN_PASS_RATE = 0.8

pytestmark = [
    pytest.mark.live_llm,
    # eval_metric here is declarative metadata (`-m eval_metric` selects this file) — the actual
    # gate is assert_min_pass_rate() below; see test_faithfulness.py's docstring for why.
    pytest.mark.eval_metric(name="answer_relevancy", threshold=MIN_PASS_RATE),
    xfail_under_ci_judge,
]


def _known_relevant_cases(golden_dataset: list[EvalCase]) -> list[EvalCase]:
    return [c for c in golden_dataset if c.metadata.get("human_relevancy") == 1.0]


def test_answer_relevancy_on_golden_set(
    golden_dataset: list[EvalCase], judge_llm: OllamaModel
) -> None:
    metric = answer_relevancy_metric(threshold=0.5, model=judge_llm)
    known_relevant = _known_relevant_cases(golden_dataset)
    assert known_relevant, "golden dataset has no human_relevancy==1.0 cases to regress on"

    results = [metric.evaluate(case) for case in known_relevant]

    assert_min_pass_rate(results, MIN_PASS_RATE)
