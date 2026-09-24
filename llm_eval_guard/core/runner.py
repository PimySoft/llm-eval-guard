"""Runs a `leg.config.yaml` suite: dataset in, every configured metric evaluated per case."""

from __future__ import annotations

from dataclasses import dataclass

from llm_eval_guard.core.config import LegConfig
from llm_eval_guard.core.dataset import load_golden_dataset
from llm_eval_guard.core.models import MetricResult
from llm_eval_guard.core.registry import build_metric


@dataclass
class CaseResult:
    """One metric's result against one case, kept alongside the case's input for reporting."""

    case_input: str
    result: MetricResult


@dataclass
class SuiteRunResult:
    suite_name: str
    case_results: list[CaseResult]

    @property
    def results(self) -> list[MetricResult]:
        return [cr.result for cr in self.case_results]


def run_suite(name: str, config: LegConfig, *, fast: bool = False) -> SuiteRunResult:
    """Run every metric in suite `name` against its dataset.

    `fast=True` skips any `MetricConfig` not marked `fast: true` — this is what lets
    `leg run --fast` stay network-free (see plan.md Phase 3.3).
    """
    try:
        suite = config.suites[name]
    except KeyError:
        raise KeyError(f"unknown suite {name!r} — known: {sorted(config.suites)}") from None

    cases = load_golden_dataset(suite.dataset)
    case_results: list[CaseResult] = []
    for metric_cfg in suite.metrics:
        if fast and not metric_cfg.fast:
            continue
        metric = build_metric(metric_cfg, config.judge)
        for case in cases:
            case_results.append(CaseResult(case_input=case.input, result=metric.evaluate(case)))

    return SuiteRunResult(suite_name=name, case_results=case_results)


def run_all(config: LegConfig, *, fast: bool = False) -> list[SuiteRunResult]:
    return [run_suite(name, config, fast=fast) for name in config.suites]
