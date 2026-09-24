"""Renders `leg run` results as a Markdown summary — the human-facing report wired into
`$GITHUB_STEP_SUMMARY` (see .github/workflows/ci.yml and docs/ci-setup.md).

Why security findings get their own section instead of sharing the "failing cases" table: a
`security`-suite failure is a different kind of finding (an attack got through) than a quality
metric dipping under threshold — the CLI's console output already makes that distinction (see
`_render_results` in cli.py); the report mirrors it.
"""

from __future__ import annotations

from llm_eval_guard.core.runner import CaseResult, SuiteRunResult

SECURITY_SUITE = "security"
MAX_FAILING_CASES = 10

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _truncate(text: str, limit: int) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _severity_rank(cr: CaseResult) -> int:
    severity = cr.metadata.get("severity", "unknown")
    return _SEVERITY_ORDER.get(severity, len(_SEVERITY_ORDER))


def render_markdown(suite_results: list[SuiteRunResult]) -> str:
    """Build the full Markdown report for one `leg run` invocation."""
    entries = [(sr.suite_name, cr) for sr in suite_results for cr in sr.case_results]
    total = len(entries)

    lines = ["# LLM-Eval-Guard Report", ""]
    if total == 0:
        lines.append("_No cases evaluated._")
        return "\n".join(lines) + "\n"

    passed = sum(1 for _, cr in entries if cr.result.passed)
    badge = "✅ PASS" if passed == total else "❌ FAIL"
    lines.append(f"**{badge}** — {passed}/{total} cases passed ({passed / total:.0%})")
    lines.append("")

    lines.append("## Per-metric summary")
    lines.append("")
    lines.append("| Suite | Metric | Cases | Passed | Pass rate | Avg score |")
    lines.append("|---|---|---|---|---|---|")
    for suite_result in suite_results:
        by_metric: dict[str, list[CaseResult]] = {}
        for cr in suite_result.case_results:
            by_metric.setdefault(cr.result.metric_name, []).append(cr)
        for metric_name, case_results in by_metric.items():
            n = len(case_results)
            n_passed = sum(1 for cr in case_results if cr.result.passed)
            avg_score = sum(cr.result.score for cr in case_results) / n
            lines.append(
                f"| {suite_result.suite_name} | {metric_name} | {n} | {n_passed} "
                f"| {n_passed / n:.0%} | {avg_score:.2f} |"
            )
    lines.append("")

    security_failures = sorted(
        (cr for suite_name, cr in entries if suite_name == SECURITY_SUITE and not cr.result.passed),
        key=_severity_rank,
    )
    if security_failures:
        lines.append("## Security findings")
        lines.append("")
        lines.append("| Severity | Category | Metric | Case | Reason |")
        lines.append("|---|---|---|---|---|")
        for cr in security_failures:
            severity = cr.metadata.get("severity", "unknown")
            category = cr.metadata.get("attack_category", "unknown")
            lines.append(
                f"| {severity} | {category} | {cr.result.metric_name} "
                f"| {_truncate(cr.case_input, 50)} | {_truncate(cr.result.reason or '', 80)} |"
            )
        lines.append("")

    other_failures = [
        (suite_name, cr)
        for suite_name, cr in entries
        if suite_name != SECURITY_SUITE and not cr.result.passed
    ]
    if other_failures:
        lines.append("## Failing cases")
        lines.append("")
        lines.append("| Suite | Metric | Case | Score | Reason |")
        lines.append("|---|---|---|---|---|")
        for suite_name, cr in other_failures[:MAX_FAILING_CASES]:
            lines.append(
                f"| {suite_name} | {cr.result.metric_name} | {_truncate(cr.case_input, 50)} "
                f"| {cr.result.score:.2f} | {_truncate(cr.result.reason or '', 80)} |"
            )
        remaining = len(other_failures) - MAX_FAILING_CASES
        if remaining > 0:
            lines.append("")
            lines.append(f"_...and {remaining} more failing case(s) — see the JSON report._")
        lines.append("")

    return "\n".join(lines) + "\n"
