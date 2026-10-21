"""Bootstrap smoke test — confirms the workspace is wired up correctly."""

import subprocess
import sys

import pytest

import llm_eval_guard


def test_package_is_importable() -> None:
    assert llm_eval_guard is not None


# A fresh interpreter per module: in-process, an earlier test's imports would mask a cycle that
# only bites when this module is the first thing a downstream user imports.
@pytest.mark.parametrize(
    "module",
    [
        "llm_eval_guard.security",
        "llm_eval_guard.schema",
        "llm_eval_guard.metrics.context_recall",
        "llm_eval_guard.metrics.deepeval_adapter",
        "llm_eval_guard.prompts",
        "llm_eval_guard.reporting",
        "llm_eval_guard.cli",
    ],
)
def test_subpackage_imports_cold_without_a_cycle(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_core_re_exports_the_runner_lazily() -> None:
    from llm_eval_guard import core
    from llm_eval_guard.core import runner

    assert core.run_suite is runner.run_suite
    with pytest.raises(AttributeError, match="no_such_name"):
        _ = core.no_such_name
