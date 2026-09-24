"""Proves the shipped datasets/redteam/*.jsonl files satisfy the dataset contract documented in
datasets/redteam/README.md and CONTRIBUTING.md ("Adding red-team content") — every entry carries
attack_category/severity/expected_behavior, and injection-style attacks carry the marker lists
ComplianceMetric/TaskCompletionMetric read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_eval_guard.core.dataset import load_golden_dataset

REDTEAM_DIR = Path(__file__).parent.parent.parent / "datasets" / "redteam"

MARKER_CATEGORIES = {"direct_prompt_injection", "indirect_prompt_injection", "jailbreak"}


@pytest.mark.parametrize(
    "filename",
    ["prompt_injection.jsonl", "indirect_injection.jsonl", "jailbreak.jsonl", "pii_leakage.jsonl"],
)
def test_redteam_dataset_entries_carry_required_metadata(filename: str) -> None:
    cases = load_golden_dataset(REDTEAM_DIR / filename)

    assert len(cases) >= 4
    for case in cases:
        assert case.metadata.get("attack_category")
        assert case.metadata.get("severity") in {"low", "medium", "high", "critical"}
        assert case.metadata.get("expected_behavior")

        if case.metadata["attack_category"] in MARKER_CATEGORIES:
            assert isinstance(case.metadata.get("compliance_markers"), list)
            assert isinstance(case.metadata.get("task_markers"), list)


def test_indirect_injection_cases_carry_poisoned_context() -> None:
    cases = load_golden_dataset(REDTEAM_DIR / "indirect_injection.jsonl")

    for case in cases:
        assert case.retrieval_context, f"{case.input!r} is missing its poisoned retrieval_context"
