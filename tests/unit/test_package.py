"""Bootstrap smoke test — confirms the workspace is wired up correctly."""

import llm_eval_guard


def test_package_is_importable() -> None:
    assert llm_eval_guard is not None
