"""Runs a `leg.config.yaml` suite: dataset in, every configured metric evaluated per case."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llm_eval_guard.core.cache import ResultCache
from llm_eval_guard.core.config import LegConfig
from llm_eval_guard.core.dataset import load_dataset_cases
from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult
from llm_eval_guard.core.registry import build_metric, load_generator
from llm_eval_guard.metrics.deepeval_adapter import resolve_judge_model_name


@dataclass
class CaseResult:
    """One metric's result against one case, kept alongside the case's input/metadata for
    reporting — e.g. the CLI reads `metadata["severity"]`/`metadata["attack_category"]` to set
    off security-suite failures from quality ones (see plan.md Phase 4.5)."""

    case_input: str
    result: MetricResult
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_security(self) -> bool:
        """A red-team case, whichever suite runs it (`security`, or `demo_security` against the
        demo app) — every red-team entry carries an `attack_category`."""
        return "attack_category" in self.metadata


@dataclass
class SuiteRunResult:
    suite_name: str
    case_results: list[CaseResult]
    skipped_reason: str | None = None

    @property
    def results(self) -> list[MetricResult]:
        return [cr.result for cr in self.case_results]


_JUDGE_ERROR = "judge error"


def _evaluate(metric: Metric, case: EvalCase, *, judge: bool) -> MetricResult:
    """A judge call that errors (e.g. a small judge looping until DeepEval's timeout) fails that
    one case instead of crashing the run. Rule-based metrics still raise — there an exception
    is a bug, not model flakiness. Errored results are never cached, so the next run retries."""
    if not judge:
        return metric.evaluate(case)
    try:
        return metric.evaluate(case)
    except Exception as exc:
        return MetricResult(
            metric_name=metric.name,
            score=0.0,
            passed=False,
            reason=f"{_JUDGE_ERROR}: {type(exc).__name__}: {exc}"[:300],
        )


def run_suite(
    name: str, config: LegConfig, *, fast: bool = False, cache: ResultCache | None = None
) -> SuiteRunResult:
    """Run every metric in suite `name` against its dataset (after its `generator`, if any,
    has produced each case's output from the system under test).

    `fast=True` skips any `MetricConfig` not marked `fast: true` — this is what lets
    `leg run --fast` stay network-free (see plan.md Phase 3.3).

    `cache`, when given, is consulted/populated only for non-`fast` (judge) metrics — see
    core/cache.py for why fast/rule-based metrics skip it.
    """
    try:
        suite = config.suites[name]
    except KeyError:
        raise KeyError(f"unknown suite {name!r} — known: {sorted(config.suites)}") from None

    if suite.generator is not None:
        if fast:
            # Why skip rather than run the fast metrics: generating needs the system under test
            # (an LLM call), and `--fast` promises zero network calls.
            return SuiteRunResult(name, [], skipped_reason="generator suite — needs the app")
        generate = load_generator(suite.generator)
        cases = [generate(c) for c in load_dataset_cases(suite.dataset, require_output=False)]
    else:
        cases = load_dataset_cases(suite.dataset)
    case_results: list[CaseResult] = []
    for metric_cfg in suite.metrics:
        if fast and not metric_cfg.fast:
            continue
        metric = build_metric(metric_cfg, config.judge)
        # A cached score is only valid for the judge and threshold that produced it.
        scope = f"{resolve_judge_model_name(config.judge.model)}@{metric.threshold}"
        for case in cases:
            result: MetricResult | None = None
            if cache is not None and not metric_cfg.fast:
                result = cache.get(metric.name, case, scope)
            if result is None:
                result = _evaluate(metric, case, judge=not metric_cfg.fast)
                errored = result.reason is not None and result.reason.startswith(_JUDGE_ERROR)
                if cache is not None and not metric_cfg.fast and not errored:
                    cache.set(metric.name, case, result, scope)
            case_results.append(
                CaseResult(case_input=case.input, result=result, metadata=case.metadata)
            )

    return SuiteRunResult(suite_name=name, case_results=case_results)


def run_all(
    config: LegConfig, *, fast: bool = False, cache: ResultCache | None = None
) -> list[SuiteRunResult]:
    return [run_suite(name, config, fast=fast, cache=cache) for name in config.suites]
