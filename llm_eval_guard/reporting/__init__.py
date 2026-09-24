"""Markdown/JSON report generators for `leg run` results — see docs/ci-setup.md."""

from __future__ import annotations

from llm_eval_guard.reporting.json_report import render_json, to_report_dict
from llm_eval_guard.reporting.markdown_report import render_markdown

__all__ = ["render_json", "render_markdown", "to_report_dict"]
