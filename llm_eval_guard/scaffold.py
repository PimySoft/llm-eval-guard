"""Scaffolding for `leg init` — writes a starter `leg.config.yaml`, a sample golden-dataset case,
and an example pytest test into a downstream project.

Why ship a sample dataset too, not just a config: a `leg.config.yaml` that points at a dataset
file that doesn't exist yet fails on the very first `leg run` a new adopter tries — the scaffold
has to leave the project in a runnable state, not just a configured one.
"""

from __future__ import annotations

from pathlib import Path

LEG_CONFIG = """\
# Scaffolded by `leg init` — see docs/architecture.md for the full leg.config.yaml reference
# (in the llm-eval-guard repo) and docs/thresholds.md for guidance on tuning these numbers.
suites:
  quality:
    dataset: datasets/golden/sample.jsonl
    metrics:
      - name: faithfulness
        threshold: 0.8
      - name: answer_relevancy
        threshold: 0.8

judge:
  model: qwen2.5:0.5b
  base_url: http://localhost:11434
"""

SAMPLE_DATASET = (
    '{"input": "What is the return window on Aperture orders?", '
    '"actual_output": "Aperture orders can be returned within 30 days of delivery for a full '
    'refund.", "retrieval_context": ["Aperture return policy: items may be returned within 30 '
    'days of delivery for a full refund. Items must be unused and in original packaging."], '
    '"metadata": {"note": "Replace this with real cases from your own RAG pipeline."}}\n'
)

EXAMPLE_TEST = '''\
"""Example eval test scaffolded by `leg init`. Swap the hardcoded EvalCase below for one built
from your real LLM/RAG pipeline's output (wire it in via the `eval_client` fixture in your own
conftest.py — see llm_eval_guard.pytest_plugin) once you're ready to test it for real.

Requires Ollama running locally (`ollama pull qwen2.5:0.5b`) — this test carries
`@pytest.mark.live_llm` so it auto-skips instead of failing if Ollama isn't reachable.
"""

from __future__ import annotations

import pytest

from llm_eval_guard.core.models import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import faithfulness_metric
from llm_eval_guard.pytest_plugin import assert_eval_metric


@pytest.mark.live_llm
@pytest.mark.eval_metric(name="faithfulness", threshold=0.8)
def test_sample_answer_is_faithful(judge_llm, request):
    case = EvalCase(
        input="What is the return window on Aperture orders?",
        actual_output=(
            "Aperture orders can be returned within 30 days of delivery for a full refund."
        ),
        retrieval_context=[
            "Aperture return policy: items may be returned within 30 days of delivery for a "
            "full refund. Items must be unused and in original packaging."
        ],
    )
    result = faithfulness_metric(threshold=0.8, model=judge_llm).evaluate(case)
    assert_eval_metric(result, request)
'''

# (relative path, content) — order matters for the CLI's "created" listing.
SCAFFOLD_FILES: tuple[tuple[str, str], ...] = (
    ("leg.config.yaml", LEG_CONFIG),
    ("datasets/golden/sample.jsonl", SAMPLE_DATASET),
    ("tests/test_llm_eval_guard_example.py", EXAMPLE_TEST),
)


def scaffold_project(directory: Path, *, force: bool = False) -> list[Path]:
    """Write the starter files into `directory`, skipping any that already exist unless `force`.

    Returns the paths actually written, in `SCAFFOLD_FILES` order.
    """
    written: list[Path] = []
    for relative_path, content in SCAFFOLD_FILES:
        path = directory / relative_path
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
