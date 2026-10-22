from __future__ import annotations

from llm_eval_guard.core.models import MetricResult
from llm_eval_guard.core.runner import CaseResult, SuiteRunResult
from llm_eval_guard.reporting.json_report import render_json, to_report_dict
from llm_eval_guard.reporting.markdown_report import render_markdown


def _case_result(
    *, metric: str = "faithfulness", score: float = 0.9, passed: bool = True, **metadata: object
) -> CaseResult:
    return CaseResult(
        case_input="what is the storage limit?",
        result=MetricResult(metric_name=metric, score=score, passed=passed, reason="because"),
        metadata=dict(metadata),
    )


def test_render_markdown_empty_run_says_no_cases() -> None:
    assert "No cases evaluated" in render_markdown([])


def test_render_markdown_all_pass_shows_pass_badge() -> None:
    suite = SuiteRunResult(suite_name="quality", case_results=[_case_result()])

    out = render_markdown([suite])

    assert "✅ PASS" in out
    assert "1/1 cases passed" in out
    assert "## Failing cases" not in out


def test_render_markdown_failure_appears_in_failing_cases_list() -> None:
    suite = SuiteRunResult(
        suite_name="quality", case_results=[_case_result(passed=False, score=0.2)]
    )

    out = render_markdown([suite])

    assert "❌ FAIL" in out
    assert "## Failing cases" in out
    assert "faithfulness" in out


def test_render_markdown_security_failure_goes_to_security_section_not_failing_cases() -> None:
    suite = SuiteRunResult(
        suite_name="security",
        case_results=[
            _case_result(
                metric="compliance",
                passed=False,
                score=0.0,
                severity="critical",
                attack_category="direct_prompt_injection",
            )
        ],
    )

    out = render_markdown([suite])

    assert "## Security findings" in out
    assert "critical" in out
    assert "direct_prompt_injection" in out
    assert "## Failing cases" not in out


def test_render_markdown_sorts_security_findings_by_severity() -> None:
    suite = SuiteRunResult(
        suite_name="security",
        case_results=[
            _case_result(metric="pii_leakage", passed=False, severity="low", attack_category="pii"),
            _case_result(
                metric="compliance", passed=False, severity="critical", attack_category="dpi"
            ),
        ],
    )

    out = render_markdown([suite])
    critical_pos = out.index("critical")
    low_pos = out.index("**low**")

    assert critical_pos < low_pos


def test_to_report_dict_counts_pass_fail() -> None:
    suite = SuiteRunResult(
        suite_name="quality",
        case_results=[_case_result(passed=True), _case_result(passed=False)],
    )

    report = to_report_dict([suite])

    assert report["total_cases"] == 2
    assert report["passed_cases"] == 1
    assert report["passed"] is False
    assert len(report["cases"]) == 2


def test_render_json_round_trips_through_json_module() -> None:
    import json

    suite = SuiteRunResult(suite_name="quality", case_results=[_case_result()])

    parsed = json.loads(render_json([suite]))

    assert parsed["passed"] is True
    assert parsed["cases"][0]["metric"] == "faithfulness"


def test_render_markdown_treats_red_team_cases_in_any_suite_as_security_findings() -> None:
    suite = SuiteRunResult(
        suite_name="demo_security",
        case_results=[
            _case_result(
                metric="compliance", passed=False, severity="high", attack_category="jailbreak"
            )
        ],
    )

    out = render_markdown([suite])

    assert "## Security findings" in out
    assert "## Failing cases" not in out


def test_render_markdown_uses_bullet_lists_not_tables() -> None:
    suite = SuiteRunResult(
        suite_name="quality",
        case_results=[
            _case_result(),
            _case_result(passed=False, score=0.2),
            _case_result(metric="compliance", passed=False, severity="high", attack_category="dpi"),
        ],
    )

    out = render_markdown([suite])

    assert "|" not in out
    assert "- **quality / faithfulness** — 1/2 passed (50%), avg score 0.55" in out
    assert "- **quality / faithfulness** — score 0.20 — “what is the storage limit?”" in out
    assert "  - Reason: because" in out
