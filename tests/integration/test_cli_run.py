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
