"""Example strict output schemas demonstrating the pattern consumers should follow.

Why ship examples instead of only the generic validator: `SchemaValidationMetric` (validation.py)
works with *any* Pydantic model, but a bare validator with no example schema leaves the "what does
a contract look like" question unanswered — these two cover the common RAG-answer and
tool-calling-output shapes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RagAnswer(BaseModel):
    """A RAG pipeline's structured answer: the answer text plus its cited sources."""

    answer: str
    sources: list[str]
    confidence: float


class ToolCallOutput(BaseModel):
    """A single tool-calling decision emitted by an LLM agent."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str | None = None
