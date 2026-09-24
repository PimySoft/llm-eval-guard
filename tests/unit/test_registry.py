from __future__ import annotations

import pytest

from llm_eval_guard.core.config import JudgeConfig, MetricConfig
from llm_eval_guard.core.registry import build_metric
from llm_eval_guard.schema.validation import SchemaValidationMetric


def test_build_metric_resolves_faithfulness() -> None:
    metric = build_metric(MetricConfig(name="faithfulness", threshold=0.7), JudgeConfig())

    assert metric.name == "faithfulness"
    assert metric.threshold == 0.7


def test_build_metric_resolves_schema_prefix() -> None:
    metric = build_metric(
        MetricConfig(name="schema:llm_eval_guard.schema.models:ToolCallOutput"),
        JudgeConfig(),
    )

    assert isinstance(metric, SchemaValidationMetric)
    assert metric.name == "schema:ToolCallOutput"


def test_build_metric_unknown_name_lists_known_names() -> None:
    with pytest.raises(ValueError, match="unknown metric 'nope'"):
        build_metric(MetricConfig(name="nope"), JudgeConfig())


def test_build_metric_malformed_schema_reference_raises() -> None:
    with pytest.raises(ValueError, match="malformed schema reference"):
        build_metric(MetricConfig(name="schema:not-a-valid-ref"), JudgeConfig())


def test_build_metric_resolves_toxicity_with_its_own_default_threshold() -> None:
    metric = build_metric(MetricConfig(name="toxicity"), JudgeConfig())

    assert metric.name == "toxicity"
    assert metric.threshold == 0.5


@pytest.mark.parametrize("name", ["compliance", "task_completion", "pii_leakage"])
def test_build_metric_resolves_rule_based_security_metrics(name: str) -> None:
    metric = build_metric(MetricConfig(name=name, threshold=0.9), JudgeConfig())

    assert metric.name == name
    assert metric.threshold == 0.9


def test_build_metric_rule_based_security_metric_defaults_threshold_to_one() -> None:
    metric = build_metric(MetricConfig(name="compliance"), JudgeConfig())

    assert metric.threshold == 1.0
