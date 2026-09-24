"""Machine-readable counterpart to markdown_report.py — same data, JSON-shaped for future
dashboarding/trend tracking (plan.md Phase 5.3) rather than for human reading in a PR.
"""

from __future__ import annotations

import json
from typing import Any

from llm_eval_guard.core.runner import SuiteRunResult


def to_report_dict(suite_results: list[SuiteRunResult]) -> dict[str, Any]:
    """Build the plain-dict report payload (before JSON serialization) so callers can also embed
    it in a larger structure without reparsing."""
    cases: list[dict[str, Any]] = []
    total = 0
    passed = 0
    for suite_result in suite_results:
        for case_result in suite_result.case_results:
            total += 1
            passed += int(case_result.result.passed)
            cases.append(
                {
                    "suite": suite_result.suite_name,
                    "metric": case_result.result.metric_name,
                    "case_input": case_result.case_input,
                    "score": case_result.result.score,
                    "passed": case_result.result.passed,
                    "reason": case_result.result.reason,
                    "metadata": case_result.metadata,
                }
            )
    return {
        "passed": passed == total,
        "total_cases": total,
        "passed_cases": passed,
        "cases": cases,
    }


def render_json(suite_results: list[SuiteRunResult]) -> str:
    return json.dumps(to_report_dict(suite_results), indent=2, sort_keys=True)
