"""The `leg` CLI — `leg run` executes a `leg.config.yaml` suite and gates on the results.

Why Typer: it's already a core dependency (see pyproject.toml), builds on click (well-understood
testing story via `typer.testing.CliRunner`), and derives `--help` from type hints/docstrings
instead of hand-written argparse boilerplate.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from llm_eval_guard.core.cache import DEFAULT_CACHE_PATH, ResultCache
from llm_eval_guard.core.config import load_config
from llm_eval_guard.core.runner import CaseResult, SuiteRunResult, run_all, run_suite
from llm_eval_guard.reporting import render_json, render_markdown
from llm_eval_guard.scaffold import scaffold_project

app = typer.Typer(add_completion=False)
console = Console()


@app.callback()
def main() -> None:
    """LLM-Eval-Guard: pytest-native CI/CD quality gate for LLM/RAG apps.

    Why an (otherwise empty) callback: Typer collapses a single `@app.command()` into a bare
    `leg [OPTIONS]` invocation with no subcommand name — registering a callback forces `leg run
    ...`/`leg init ...` to stay the real, stable CLI surface (matching plan.md) rather than
    collapsing to a single bare `leg [OPTIONS]`.
    """


_SECURITY_SUITE = "security"


def _render_results(suite_results: list[SuiteRunResult]) -> bool:
    """Print a Rich pass/fail table + summary; return True iff every result passed.

    Security-suite failures are rendered distinctly from quality/schema ones (bold + a category/
    severity label instead of a bare "fail") and called out again in their own summary line — a
    security regression is a different kind of finding than a faithfulness score dipping under
    threshold, and plan.md Phase 4.5 asks for that to be visually obvious, not just a row in a
    shared table (the Markdown/JSON report from `--report-dir` mirrors this — see reporting/).
    """
    table = Table(title="leg run results")
    table.add_column("Suite")
    table.add_column("Metric")
    table.add_column("Case")
    table.add_column("Score", justify="right")
    table.add_column("Result")

    all_passed = True
    total = 0
    passed = 0
    security_failures: list[CaseResult] = []
    for suite_result in suite_results:
        is_security = suite_result.suite_name == _SECURITY_SUITE
        for case_result in suite_result.case_results:
            total += 1
            result = case_result.result
            if result.passed:
                passed += 1
                result_label = "[green]pass[/green]"
            else:
                all_passed = False
                if is_security:
                    security_failures.append(case_result)
                    severity = case_result.metadata.get("severity", "unknown")
                    result_label = f"[bold red]SECURITY FAIL ({severity})[/bold red]"
                else:
                    result_label = "[red]fail[/red]"
            case_label = (
                case_result.case_input
                if len(case_result.case_input) <= 60
                else case_result.case_input[:57] + "..."
            )
            table.add_row(
                suite_result.suite_name,
                result.metric_name,
                case_label,
                f"{result.score:.2f}",
                result_label,
            )

    console.print(table)
    if total == 0:
        console.print("[yellow]no cases evaluated[/yellow]")
        return True

    summary_style = "green" if all_passed else "red"
    console.print(f"[{summary_style}]{passed}/{total} passed ({passed / total:.0%})[/]")
    if security_failures:
        console.print(
            f"[bold red]⚠ {len(security_failures)} security finding(s) — blocking by default[/]"
        )
    return all_passed


@app.command()
def run(
    suite: str = typer.Option(
        "all", "--suite", help="Suite name from leg.config.yaml, or 'all' to run every suite."
    ),
    # str, not Path: ruff's B008 (flake8-bugbear) only recognizes typer.Option as a safe
    # default-call pattern for a handful of primitive annotation types — Path isn't one of them,
    # so a Path-typed default here false-positives as a mutable-default-argument lint error.
    config: str = typer.Option("leg.config.yaml", "--config", help="Path to the leg config file."),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Skip metrics not marked fast: true (schema/prompt-drift-style checks only) — "
        "no network calls, safe to run on every commit.",
    ),
    cache: bool = typer.Option(
        True,
        "--cache/--no-cache",
        help="Reuse judge-metric results from .leg_cache/ for unchanged (metric, case) pairs — "
        "saves CI time, not money, since the judge model is already $0 (see docs/ci-setup.md).",
    ),
    report_dir: str | None = typer.Option(
        None,
        "--report-dir",
        help="Write report.md and report.json summarizing the run to this directory "
        "(see docs/ci-setup.md for wiring report.md into a GitHub Actions job summary).",
    ),
) -> None:
    """Run an eval suite and exit non-zero if any case fails."""
    leg_config = load_config(Path(config))
    result_cache = ResultCache(DEFAULT_CACHE_PATH) if cache else None

    if suite == "all":
        suite_results = run_all(leg_config, fast=fast, cache=result_cache)
    else:
        suite_results = [run_suite(suite, leg_config, fast=fast, cache=result_cache)]

    if result_cache is not None:
        result_cache.save()

    if report_dir is not None:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.md").write_text(render_markdown(suite_results), encoding="utf-8")
        (out_dir / "report.json").write_text(render_json(suite_results), encoding="utf-8")

    all_passed = _render_results(suite_results)
    raise typer.Exit(code=0 if all_passed else 1)


@app.command()
def init(
    directory: str = typer.Option(
        ".", "--dir", help="Project directory to scaffold into (created if missing)."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite scaffolded files that already exist."
    ),
) -> None:
    """Scaffold a starter leg.config.yaml, sample dataset, and example test into a project."""
    written = scaffold_project(Path(directory), force=force)
    if not written:
        console.print(
            "[yellow]Nothing to scaffold — all target files already exist (use --force to "
            "overwrite).[/yellow]"
        )
        raise typer.Exit(code=0)

    console.print("[green]Scaffolded:[/green]")
    for path in written:
        console.print(f"  {path}")
    console.print(
        "\nNext: `ollama pull qwen2.5:0.5b`, then `leg run --config "
        f"{Path(directory) / 'leg.config.yaml'}`."
    )


if __name__ == "__main__":
    app()
