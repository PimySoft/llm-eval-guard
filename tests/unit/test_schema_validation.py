from __future__ import annotations

import json

from llm_eval_guard.core import EvalCase
from llm_eval_guard.schema import SchemaValidationMetric, ToolCallOutput

VALID_PAYLOAD = {"tool_name": "search", "arguments": {"query": "weather"}, "call_id": "call_1"}


def _case(payload: object) -> EvalCase:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return EvalCase(input="call a tool", actual_output=body)


def test_valid_payload_passes_strict() -> None:
    metric = SchemaValidationMetric(ToolCallOutput, strict=True)

    result = metric.evaluate(_case(VALID_PAYLOAD))

    assert result.passed is True
    assert result.score == 1.0
    assert result.reason is None


def test_malformed_json_fails_gracefully_in_both_modes() -> None:
    strict = SchemaValidationMetric(ToolCallOutput, strict=True)
    lenient = SchemaValidationMetric(ToolCallOutput, strict=False)
    case = _case("{not json")

    strict_result = strict.evaluate(case)
    lenient_result = lenient.evaluate(case)

    assert strict_result.passed is False
    assert lenient_result.passed is False
    assert "invalid JSON" in (strict_result.reason or "")
    assert "invalid JSON" in (lenient_result.reason or "")


def test_missing_required_field_fails_strict_with_clear_message() -> None:
    metric = SchemaValidationMetric(ToolCallOutput, strict=True)
    payload = {"arguments": {"query": "weather"}}

    result = metric.evaluate(_case(payload))

    assert result.passed is False
    assert result.score == 0.0
    assert result.reason is not None
    assert "tool_name" in result.reason


def test_extra_field_fails_strict_but_only_warns_lenient() -> None:
    payload = {**VALID_PAYLOAD, "confidence": 0.9}
    strict_result = SchemaValidationMetric(ToolCallOutput, strict=True).evaluate(_case(payload))
    lenient_result = SchemaValidationMetric(ToolCallOutput, strict=False).evaluate(_case(payload))

    assert strict_result.passed is False
    assert "confidence" in (strict_result.reason or "")

    assert lenient_result.passed is True
    assert lenient_result.reason is not None
    assert "warnings" in lenient_result.reason


def test_strict_and_lenient_metrics_do_not_leak_policy_between_each_other() -> None:
    strict = SchemaValidationMetric(ToolCallOutput, strict=True)
    lenient = SchemaValidationMetric(ToolCallOutput, strict=False)
    payload = {**VALID_PAYLOAD, "confidence": 0.9}

    # Interleaved on purpose: evaluating lenient first must not make the strict instance lenient.
    assert lenient.evaluate(_case(payload)).passed is True
    assert strict.evaluate(_case(payload)).passed is False
