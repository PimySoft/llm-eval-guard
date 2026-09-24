"""Maps `leg.config.yaml` metric names to concrete `Metric` instances.

Why a registry instead of importing metric factories directly in `leg.config.yaml`: config stays
plain data (a name string), not executable references — the registry is the one place that
resolves names to code, which is what makes `core/runner.py` and the CLI config-agnostic.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from llm_eval_guard.core.config import JudgeConfig, MetricConfig
from llm_eval_guard.core.metric import Metric
from llm_eval_guard.metrics.deepeval_adapter import (
    answer_relevancy_metric,
    contextual_precision_metric,
    faithfulness_metric,
    judge_model,
)
from llm_eval_guard.schema.validation import SchemaValidationMetric

_JudgeMetricFactory = Callable[[float, Any], Metric]

# Built-in LLM-judge metric factories. Whether a given leg.config.yaml entry runs under
# `--fast` is config's call (MetricConfig.fast, see core/config.py), not this registry's — a
# factory here has no opinion on speed, it just builds the metric.
_JUDGE_METRICS: dict[str, _JudgeMetricFactory] = {
    "faithfulness": faithfulness_metric,
    "answer_relevancy": answer_relevancy_metric,
    "contextual_precision": contextual_precision_metric,
}

_SCHEMA_PREFIX = "schema:"


def _import_schema(dotted: str) -> type[BaseModel]:
    """Resolve `module.path:ClassName` to a Pydantic model class."""
    module_path, _, class_name = dotted.partition(":")
    if not module_path or not class_name:
        raise ValueError(
            f"malformed schema reference {dotted!r} — expected 'module.path:ClassName'"
        )
    module = importlib.import_module(module_path)
    schema = getattr(module, class_name)
    if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
        raise ValueError(f"{dotted!r} is not a Pydantic BaseModel subclass")
    return schema


def build_metric(cfg: MetricConfig, judge: JudgeConfig) -> Metric:
    """Build the `Metric` a `MetricConfig` entry describes."""
    if cfg.name.startswith(_SCHEMA_PREFIX):
        schema = _import_schema(cfg.name.removeprefix(_SCHEMA_PREFIX))
        return SchemaValidationMetric(schema, strict=True, threshold=cfg.threshold or 1.0)

    factory = _JUDGE_METRICS.get(cfg.name)
    if factory is None:
        raise ValueError(
            f"unknown metric {cfg.name!r} — known: {sorted(_JUDGE_METRICS)}, "
            f"or '{_SCHEMA_PREFIX}module.path:ClassName'"
        )
    model = judge_model(judge.model, judge.base_url)
    return factory(cfg.threshold or 0.8, model)
