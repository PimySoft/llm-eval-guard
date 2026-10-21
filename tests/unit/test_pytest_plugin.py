"""Exercises llm_eval_guard.pytest_plugin's marker/fixture/hook behavior via pytest's `pytester`
fixture — the recommended way to test a pytest plugin end-to-end, rather than hand-faking a
FixtureRequest.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _inner_run_config(pytester: pytest.Pytester) -> None:
    """The inner run doesn't see this repo's pyproject.toml; without this, pytest-asyncio (pulled
    in by deepeval) emits its unset-loop-scope deprecation warning in every inner session."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")


def test_eval_metric_marker_gates_on_declared_threshold(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        from llm_eval_guard.core.models import MetricResult
        from llm_eval_guard.pytest_plugin import assert_eval_metric

        @pytest.mark.eval_metric(name="faithfulness", threshold=0.8)
        def test_above_threshold(request):
            result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason=None)
            assert_eval_metric(result, request)

        @pytest.mark.eval_metric(name="faithfulness", threshold=0.8)
        def test_below_threshold(request):
            result = MetricResult(
                metric_name="faithfulness", score=0.3, passed=False, reason="bad"
            )
            assert_eval_metric(result, request)
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1, failed=1)


def test_assert_eval_metric_requires_the_marker(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from llm_eval_guard.core.models import MetricResult
        from llm_eval_guard.pytest_plugin import assert_eval_metric

        def test_missing_marker(request):
            result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason=None)
            assert_eval_metric(result, request)
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(failed=1)


def test_eval_client_default_raises_not_implemented(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        def test_it(eval_client):
            with pytest.raises(NotImplementedError):
                eval_client("hi")
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_live_llm_tests_are_skipped_when_ollama_unreachable(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")  # nothing listens on port 1
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.live_llm
        def test_it():
            raise AssertionError("should have been skipped")
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(skipped=1)
