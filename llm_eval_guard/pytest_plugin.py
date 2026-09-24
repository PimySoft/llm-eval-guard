"""Pytest plugin entry point — registered under ``[project.entry-points.pytest11]`` so any repo
that installs ``llm-eval-guard`` gets the ``eval_metric`` marker and ``judge_llm``/``eval_client``
fixtures automatically, without needing its own conftest.py boilerplate.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
import requests

from llm_eval_guard.core.models import MetricResult

if TYPE_CHECKING:
    from deepeval.models.llms import OllamaModel

# The type of "the thing being evaluated": a callable that turns a prompt into the system's
# response. Downstream repos override the `eval_client` fixture with one that calls their own
# LLM/RAG pipeline; there's no sane framework-wide default, so the built-in one just explains that.
EvalClient = Callable[[str], str]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Overwrite prompt-drift snapshots (llm_eval_guard.prompts.snapshot) to match the "
        "current render instead of failing on drift.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "eval_metric(name, threshold): declarative metric threshold assertion",
    )
    config.addinivalue_line(
        "markers",
        "live_llm: exercises a real local Ollama call (skipped automatically if unreachable)",
    )
    config.addinivalue_line(
        "markers",
        "calibration: judge calibration check against human-labeled ground truth",
    )


def _ollama_reachable(base_url: str) -> bool:
    try:
        requests.get(base_url, timeout=1)
        return True
    except requests.RequestException:
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip ``live_llm``-marked tests when no local Ollama server is reachable, so
    ``pytest``/``make test`` stays green on a machine (or CI job) that never installed Ollama —
    see Phase 2.2's CI-safe-by-default requirement in plan.md."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    if _ollama_reachable(base_url):
        return
    skip_live = pytest.mark.skip(reason=f"Ollama not reachable at {base_url}")
    for item in items:
        if "live_llm" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def judge_llm() -> OllamaModel:
    """The local Ollama model DeepEval metrics grade against — see metrics/deepeval_adapter.py
    for why this is Ollama and not a paid API by default."""
    from llm_eval_guard.metrics.deepeval_adapter import judge_model

    return judge_model()


@pytest.fixture
def update_snapshots(request: pytest.FixtureRequest) -> bool:
    """Whether `pytest --update-snapshots` was passed — see prompts/snapshot.py."""
    value = request.config.getoption("--update-snapshots")
    return bool(value)


@pytest.fixture
def eval_client() -> EvalClient:
    """The LLM/RAG pipeline under test. Not implemented here on purpose — this package tests
    *your* system's outputs, it doesn't ship one. Override this fixture in your own conftest.py,
    e.g.::

        @pytest.fixture
        def eval_client():
            return my_rag_app.answer
    """

    def _not_configured(_prompt: str) -> str:
        raise NotImplementedError(
            "No eval_client configured — override the `eval_client` fixture in your conftest.py "
            "to call your own LLM/RAG pipeline."
        )

    return _not_configured


def assert_eval_metric(result: MetricResult, request: pytest.FixtureRequest) -> None:
    """Assert ``result`` clears the threshold declared by ``@pytest.mark.eval_metric`` on the
    calling test, so the threshold is written once (in the marker) instead of twice (marker +
    hand-rolled assert).
    """
    marker = request.node.get_closest_marker("eval_metric")
    if marker is None:
        raise RuntimeError(
            "assert_eval_metric() requires the calling test to carry "
            "@pytest.mark.eval_metric(name=..., threshold=...)"
        )
    threshold = marker.kwargs.get("threshold")
    name = marker.kwargs.get("name", result.metric_name)
    if threshold is not None:
        assert result.score >= threshold, (
            f"{name}: score {result.score:.2f} below threshold {threshold} — {result.reason}"
        )
    else:
        assert result.passed, f"{name}: {result.reason}"


def assert_min_pass_rate(results: list[MetricResult], min_pass_rate: float) -> None:
    """Assert at least ``min_pass_rate`` of ``results`` passed.

    Why a pass-rate bar instead of requiring every case to pass: LLM-judge metrics are
    probabilistic even with a well-calibrated model (see docs/judge-calibration.md) — gating a
    regression suite on every single score would make the suite flaky by construction. This is
    the aggregate-tolerance counterpart to :func:`assert_eval_metric`'s single-result assertion.
    """
    if not results:
        raise ValueError("assert_min_pass_rate() called with no results")
    passed = [r for r in results if r.passed]
    pass_rate = len(passed) / len(results)
    if pass_rate < min_pass_rate:
        failures = [r for r in results if not r.passed]
        detail = "; ".join(f"{r.metric_name}={r.score:.2f} ({r.reason})" for r in failures[:3])
        raise AssertionError(
            f"pass rate {pass_rate:.0%} below minimum {min_pass_rate:.0%} "
            f"({len(failures)}/{len(results)} failed): {detail}"
        )
