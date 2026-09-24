"""Runs a `leg.config.yaml` suite: dataset in, every configured metric evaluated per case."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llm_eval_guard.core.cache import ResultCache
from llm_eval_guard.core.config import LegConfig
from llm_eval_guard.core.dataset import load_dataset_cases
from llm_eval_guard.core.models import MetricResult
from llm_eval_guard.core.registry import build_metric


@dataclass
class CaseResult:
    """One metric's result against one case, kept alongside the case's input/metadata for
    reporting — e.g. the CLI reads `metadata["severity"]`/`metadata["attack_category"]` to set
    off security-suite failures from quality ones (see plan.md Phase 4.5)."""

    case_input: str
    result: MetricResult
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SuiteRunResult:
    suite_name: str
    case_results: list[CaseResult]

    @property
    def results(self) -> list[MetricResult]:
        return [cr.result for cr in self.case_results]


def run_suite(
    name: str, config: LegConfig, *, fast: bool = False, cache: ResultCache | None = None
) -> SuiteRunResult:
    """Run every metric in suite `name` against its dataset.

    `fast=True` skips any `MetricConfig` not marked `fast: true` — this is what lets
    `leg run --fast` stay network-free (see plan.md Phase 3.3).

    `cache`, when given, is consulted/populated only for non-`fast` (judge) metrics — see
    core/cache.py for why fast/rule-based metrics skip it.
    """
    try:
        suite = config.suites[name]
    except KeyError:
        raise KeyError(f"unknown suite {name!r} — known: {sorted(config.suites)}") from None

    cases = load_dataset_cases(suite.dataset)
    case_results: list[CaseResult] = []
    for metric_cfg in suite.metrics:
        if fast and not metric_cfg.fast:
            continue
        metric = build_metric(metric_cfg, config.judge)
        for case in cases:
            result: MetricResult | None = None
            if cache is not None and not metric_cfg.fast:
                result = cache.get(metric.name, case)
            if result is None:
                result = metric.evaluate(case)
                if cache is not None and not metric_cfg.fast:
                    cache.set(metric.name, case, result)
            case_results.append(
                CaseResult(case_input=case.input, result=result, metadata=case.metadata)
            )

    return SuiteRunResult(suite_name=name, case_results=case_results)


def run_all(
    config: LegConfig, *, fast: bool = False, cache: ResultCache | None = None
) -> list[SuiteRunResult]:
    return [run_suite(name, config, fast=fast, cache=cache) for name in config.suites]
