from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llm_eval_guard.core.config import LegConfig, MetricConfig, SuiteConfig, load_config
from llm_eval_guard.core.dataset import load_dataset_cases, load_golden_dataset
from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult

if TYPE_CHECKING:
    from llm_eval_guard.core.runner import CaseResult, SuiteRunResult, run_all, run_suite

# Why lazy: runner -> registry imports every metric module, and those import `core.metric` — an
# eager import here made `import llm_eval_guard.security` (or `.schema`/`.metrics`) circular.
_RUNNER_EXPORTS = {"CaseResult", "SuiteRunResult", "run_all", "run_suite"}


def __getattr__(name: str) -> Any:
    if name in _RUNNER_EXPORTS:
        from llm_eval_guard.core import runner

        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CaseResult",
    "EvalCase",
    "LegConfig",
    "Metric",
    "MetricConfig",
    "MetricResult",
    "SuiteConfig",
    "SuiteRunResult",
    "load_config",
    "load_dataset_cases",
    "load_golden_dataset",
    "run_all",
    "run_suite",
]
