"""Data models shared by every metric backend and the runner/reporting layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A single LLM/RAG interaction to score.

    ``retrieval_context`` is the set of chunks the pipeline retrieved for this input — required
    by RAG-specific metrics like faithfulness and contextual precision, optional for plain
    input/output metrics (schema validation, toxicity).
    """

    input: str
    actual_output: str
    expected_output: str | None = None
    retrieval_context: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricResult(BaseModel):
    """The normalized outcome of running one Metric against one EvalCase.

    Every adapter (DeepEval, Ragas, rule-based) must produce this shape so the runner,
    reporting, and CI threshold-gating code never need to know which engine scored a case.
    """

    metric_name: str
    score: float
    passed: bool
    reason: str | None = None
