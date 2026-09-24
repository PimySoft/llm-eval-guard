"""Loads golden/red-team datasets (JSONL) into :class:`EvalCase` objects.

Why JSONL: one case per line diffs cleanly in a PR (a changed case is a one-line diff, not a
reformatted blob), and it streams — nothing here needs the whole file materialized to start
scoring the first case.
"""

from __future__ import annotations

import json
from pathlib import Path

from llm_eval_guard.core.models import EvalCase


def load_golden_dataset(path: str | Path) -> list[EvalCase]:
    """Read a golden-dataset JSONL file into a list of :class:`EvalCase`.

    Each line is a JSON object with ``input``/``actual_output`` (required) and optional
    ``expected_output``, ``retrieval_context``, ``metadata`` — see docs/datasets.md for the full
    schema, including the ``human_faithfulness``/``human_relevancy`` labels stored in
    ``metadata`` that Phase 2.6 calibrates the judge model against.
    """
    path = Path(path)
    cases: list[EvalCase] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON — {exc}") from exc
            cases.append(EvalCase(**record))
    return cases
