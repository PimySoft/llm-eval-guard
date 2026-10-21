"""Which judge the live integration tests are running under, and the xfail that goes with it.

Why conditional: the calibrated default judge (qwen2.5:7b) is expected to pass these tests; the
fast CI smoke-check judge (qwen2.5:0.5b) is known not to (docs/judge-calibration.md). `strict=True`
so an unexpected pass under the CI judge fails loudly instead of being silently ignored.
"""

from __future__ import annotations

import os

import pytest

from llm_eval_guard.metrics.deepeval_adapter import CI_JUDGE_MODEL, DEFAULT_JUDGE_MODEL

CI_JUDGE_ACTIVE = (
    os.environ.get("LEG_JUDGE_PROFILE") == "ci"
    or os.environ.get("LEG_JUDGE_MODEL", DEFAULT_JUDGE_MODEL) == CI_JUDGE_MODEL
)

xfail_under_ci_judge = pytest.mark.xfail(
    condition=CI_JUDGE_ACTIVE,
    reason=f"CI smoke-check judge ({CI_JUDGE_MODEL}) fails calibration — see "
    "docs/judge-calibration.md",
    strict=True,
)
