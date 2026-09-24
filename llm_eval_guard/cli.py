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

from llm_eval_guard.core.config import load_config
from llm_eval_guard.core.runner import SuiteRunResult, run_all, run_suite

app = typer.Typer(add_completion=False)
console = Console()


@app.callback()
def main() -> None:
    """LLM-Eval-Guard: pytest-native CI/CD quality gate for LLM/RAG apps.

    Why an (otherwise empty) callback: Typer collapses a single `@app.command()` into a bare
    `leg [OPTIONS]` invocation with no subcommand name — registering a callback forces `leg run
    ...` to stay the real, stable CLI surface (matching plan.md) even before Phase 6 adds a
    second command (`leg init`).
    """


def _render_results(suite_results: list[SuiteRunResult]) -> bool:
    """Print a Rich pass/fail table + summary; return True iff every result passed."""
    table = Table(title="leg run results")
    table.add_column("Suite")
    table.add_column("Metric")
    table.add_column("Case")
    table.add_column("Score", justify="right")
    table.add_column("Result")

    all_passed = True
    total = 0
    passed = 0
    for suite_result in suite_results:
        for case_result in suite_result.case_results:
            total += 1
            result = case_result.result
            if result.passed:
                passed += 1
            else:
                all_passed = False
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
                "[green]pass[/green]" if result.passed else "[red]fail[/red]",
            )

    console.print(table)
    if total == 0:
        console.print("[yellow]no cases evaluated[/yellow]")
        return True

    summary_style = "green" if all_passed else "red"
    console.print(f"[{summary_style}]{passed}/{total} passed ({passed / total:.0%})[/]")
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
) -> None:
    """Run an eval suite and exit non-zero if any case fails."""
    leg_config = load_config(Path(config))

    if suite == "all":
        suite_results = run_all(leg_config, fast=fast)
    else:
        suite_results = [run_suite(suite, leg_config, fast=fast)]

    all_passed = _render_results(suite_results)
    raise typer.Exit(code=0 if all_passed else 1)


if __name__ == "__main__":
    app()
