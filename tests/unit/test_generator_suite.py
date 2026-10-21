"""Suites with a `generator` (Phase 9): the system under test fills each case at run time."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_eval_guard.cli import app
from llm_eval_guard.core.config import load_config
from llm_eval_guard.core.models import EvalCase
from llm_eval_guard.core.registry import load_generator
from llm_eval_guard.core.runner import run_suite
from llm_eval_guard.metrics.context_recall import ContextRecallMetric

GENERATED_CALLS: list[str] = []


def fake_generator(case: EvalCase) -> EvalCase:
    """Stands in for examples/demo_rag/app.py:generate — retrieves a fixed chunk."""
    GENERATED_CALLS.append(case.input)
    return case.model_copy(
        update={"actual_output": f"answer to {case.input}", "retrieval_context": ["Pro has 2TB"]}
    )


def _write_suite(tmp_path: Path, markers: list[str]) -> Path:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps({"input": "q1", "metadata": {"context_markers": markers}}) + "\n",
        encoding="utf-8",
    )
    config = tmp_path / "leg.config.yaml"
    config.write_text(
        f"""
suites:
  demo:
    dataset: {dataset}
    generator: "tests.unit.test_generator_suite:fake_generator"
    metrics:
      - name: context_recall
        fast: true
""",
        encoding="utf-8",
    )
    return config


def test_generator_fills_output_before_metrics_run(tmp_path: Path) -> None:
    GENERATED_CALLS.clear()
    config = load_config(_write_suite(tmp_path, ["2TB"]))

    result = run_suite("demo", config)

    assert GENERATED_CALLS == ["q1"]
    (case_result,) = result.case_results
    assert case_result.result.metric_name == "context_recall"
    assert case_result.result.passed


def test_fast_skips_generator_suites_without_calling_the_app(tmp_path: Path) -> None:
    GENERATED_CALLS.clear()
    config = load_config(_write_suite(tmp_path, ["2TB"]))

    result = run_suite("demo", config, fast=True)

    assert GENERATED_CALLS == []
    assert result.case_results == []
    assert result.skipped_reason


def test_cli_gates_on_a_retrieval_miss(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", "--suite", "demo", "--no-cache", "--config", str(_write_suite(tmp_path, ["5TB"]))],
    )

    assert result.exit_code == 1


def test_cli_notes_skipped_generator_suites_under_fast(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["run", "--fast", "--config", str(_write_suite(tmp_path, ["2TB"]))]
    )

    assert result.exit_code == 0
    assert "skipped demo" in result.stdout


def test_load_generator_rejects_malformed_and_non_callable_refs() -> None:
    with pytest.raises(ValueError, match="malformed"):
        load_generator("no_colon_here")
    with pytest.raises(ValueError, match="not callable"):
        load_generator("tests.unit.test_generator_suite:GENERATED_CALLS")


def test_context_recall_scores_the_fraction_of_markers_found() -> None:
    metric = ContextRecallMetric()
    case = EvalCase(
        input="q",
        actual_output="",
        retrieval_context=["The Free plan has 15GB."],
        metadata={"context_markers": ["15gb", "2TB"]},
    )

    result = metric.evaluate(case)

    assert result.score == 0.5
    assert not result.passed
    assert "2TB" in (result.reason or "")


def test_context_recall_passes_cases_without_markers() -> None:
    result = ContextRecallMetric().evaluate(EvalCase(input="q", actual_output="a"))

    assert result.passed


def test_shipped_demo_cases_are_covered_by_top3_retrieval() -> None:
    """The deterministic half of the `demo` suite, without the LLM: every required fact must be
    in the app's top-3 chunks. The regression demo (top-1) fails this — see README.md."""
    from examples.demo_rag.app import DemoRAG
    from llm_eval_guard.core.dataset import load_dataset_cases

    rag = DemoRAG()
    metric = ContextRecallMetric()
    cases = load_dataset_cases("examples/demo_rag/cases.jsonl", require_output=False)
    failed = [
        c.input
        for c in cases
        if not metric.evaluate(
            c.model_copy(update={"retrieval_context": rag.retrieve(c.input)})
        ).passed
    ]

    assert failed == []
