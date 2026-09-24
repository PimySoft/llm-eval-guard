"""CLI tests use an isolated tmp_path config/dataset (not the repo's own leg.config.yaml) so they
stay hermetic and never depend on the working directory `leg run` happens to be invoked from.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from llm_eval_guard.cli import app

runner = CliRunner()


def _write_schema_suite(tmp_path: Path, *, valid: bool) -> Path:
    dataset_path = tmp_path / "cases.jsonl"
    payload = {"tool_name": "search", "arguments": {}} if valid else {"arguments": {}}
    dataset_path.write_text(json.dumps({"input": "q", "actual_output": json.dumps(payload)}) + "\n")

    config_path = tmp_path / "leg.config.yaml"
    config_path.write_text(
        f"""
suites:
  schema:
    dataset: {dataset_path}
    metrics:
      - name: "schema:llm_eval_guard.schema.models:ToolCallOutput"
        fast: true
""",
        encoding="utf-8",
    )
    return config_path


def test_run_fast_exits_zero_on_passing_suite(tmp_path: Path) -> None:
    config_path = _write_schema_suite(tmp_path, valid=True)

    result = runner.invoke(app, ["run", "--fast", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "pass" in result.stdout


def test_run_fast_exits_one_on_failing_suite(tmp_path: Path) -> None:
    config_path = _write_schema_suite(tmp_path, valid=False)

    result = runner.invoke(app, ["run", "--fast", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "fail" in result.stdout


def test_run_unknown_suite_errors(tmp_path: Path) -> None:
    config_path = _write_schema_suite(tmp_path, valid=True)

    result = runner.invoke(app, ["run", "--suite", "nope", "--config", str(config_path)])

    assert result.exit_code != 0


def test_run_help_locks_in_cli_surface() -> None:
    result = runner.invoke(app, ["run", "--help"])

    assert result.exit_code == 0
    assert "--suite" in result.stdout
    assert "--config" in result.stdout
    assert "--fast" in result.stdout
