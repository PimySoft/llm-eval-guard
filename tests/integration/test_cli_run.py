"""End-to-end `leg run` against the repo's own leg.config.yaml `quality` suite, exercising the
real DeepEval + Ollama path. Marked `live_llm` so it auto-skips without a reachable Ollama server,
same as tests/integration/test_faithfulness.py / test_answer_relevancy.py.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from llm_eval_guard.cli import app

runner = CliRunner()

pytestmark = pytest.mark.live_llm


def test_run_quality_suite_end_to_end() -> None:
    result = runner.invoke(app, ["run", "--suite", "quality"])

    assert "leg run results" in result.stdout
    assert result.exit_code in (0, 1)


def test_run_security_suite_end_to_end() -> None:
    """Exercises compliance/task_completion/pii_leakage (rule-based) and toxicity (real Ollama
    call) together against the shipped datasets/redteam/*.jsonl — all should pass, since those
    fixtures model a properly-defended pipeline (see datasets/redteam/README.md)."""
    result = runner.invoke(app, ["run", "--suite", "security"])

    assert "leg run results" in result.stdout
    assert result.exit_code == 0


def test_run_demo_suite_end_to_end() -> None:
    """The Phase 9 demo app answers for real, then the deterministic `context_recall` gate runs —
    must pass on main; the regression-demo branch (top-1 retrieval) makes it fail."""
    result = runner.invoke(app, ["run", "--suite", "demo"])

    assert "leg run results" in result.stdout
    assert result.exit_code == 0
