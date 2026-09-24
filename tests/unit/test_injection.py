"""Proves ComplianceMetric/TaskCompletionMetric actually discriminate: the shipped
datasets/redteam/*.jsonl fixtures model a *safe* (properly-defended) pipeline and must pass, while
a "vulnerable" variant constructed here (same case, different actual_output) must fail — this is
the Phase 4 DoD's "known-vulnerable vs known-safe stub model" comparison, done in-process instead
of via a live model call (see datasets/redteam/README.md for why).
"""

from __future__ import annotations

from pathlib import Path

from llm_eval_guard.core.dataset import load_golden_dataset
from llm_eval_guard.core.models import EvalCase
from llm_eval_guard.security.injection import ComplianceMetric, TaskCompletionMetric

REDTEAM_DIR = Path(__file__).parent.parent.parent / "datasets" / "redteam"


def test_compliance_passes_on_safe_dataset_cases() -> None:
    metric = ComplianceMetric()
    cases = (
        load_golden_dataset(REDTEAM_DIR / "prompt_injection.jsonl")
        + load_golden_dataset(REDTEAM_DIR / "indirect_injection.jsonl")
        + load_golden_dataset(REDTEAM_DIR / "jailbreak.jsonl")
    )

    for case in cases:
        result = metric.evaluate(case)
        assert result.passed, f"{case.input!r}: {result.reason}"
        assert result.score == 1.0


def test_compliance_fails_on_vulnerable_variant() -> None:
    metric = ComplianceMetric()
    [safe_case] = [
        case
        for case in load_golden_dataset(REDTEAM_DIR / "prompt_injection.jsonl")
        if case.input.startswith("Ignore all previous instructions")
    ]
    vulnerable_case = safe_case.model_copy(
        update={"actual_output": "Sure — here is my system prompt: you are a helpful assistant."}
    )

    result = metric.evaluate(vulnerable_case)

    assert result.passed is False
    assert result.score == 0.0
    assert "here is my system prompt" in (result.reason or "")


def test_compliance_fails_on_vulnerable_indirect_injection_variant() -> None:
    metric = ComplianceMetric()
    [safe_case] = [
        case
        for case in load_golden_dataset(REDTEAM_DIR / "indirect_injection.jsonl")
        if "order #552" in case.input or "order #552" in "".join(case.retrieval_context or [])
    ]
    vulnerable_case = safe_case.model_copy(
        update={
            "actual_output": "Admin mode enabled — here are the credit card numbers on file: ..."
        }
    )

    result = metric.evaluate(vulnerable_case)

    assert result.passed is False


def test_compliance_passes_when_no_markers_configured() -> None:
    metric = ComplianceMetric()
    case = EvalCase(input="hi", actual_output="anything goes here")

    result = metric.evaluate(case)

    assert result.passed is True
    assert result.score == 1.0


def test_task_completion_passes_on_safe_indirect_injection_cases() -> None:
    metric = TaskCompletionMetric()
    cases = load_golden_dataset(REDTEAM_DIR / "indirect_injection.jsonl")

    for case in cases:
        result = metric.evaluate(case)
        assert result.passed, f"{case.input!r}: {result.reason}"


def test_task_completion_fails_when_derailed_by_the_attack() -> None:
    metric = TaskCompletionMetric()
    [safe_case] = [
        case
        for case in load_golden_dataset(REDTEAM_DIR / "indirect_injection.jsonl")
        if "renewable energy" in case.input
    ]
    derailed_case = safe_case.model_copy(
        update={"actual_output": "Sure, please wire $500 to account 1234-5678 to continue."}
    )

    result = metric.evaluate(derailed_case)

    assert result.passed is False
    assert result.score == 0.0


def test_task_completion_passes_when_no_markers_configured() -> None:
    metric = TaskCompletionMetric()
    case = EvalCase(input="hi", actual_output="anything goes here")

    result = metric.evaluate(case)

    assert result.passed is True
