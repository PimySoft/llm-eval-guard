"""Parses `leg.config.yaml`: which suites exist, which metrics each one runs, and judge settings.

Why YAML over the JSONL used for datasets: this is hand-edited human config (thresholds, suite
names), not a stream of records — YAML is what a contributor actually wants to open and tweak.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class MetricConfig(BaseModel):
    """One metric entry inside a suite.

    `name` is a registry key (`core/registry.py`): a built-in name like `faithfulness`, or
    `schema:module.path:ClassName` to validate against a caller's own Pydantic schema.
    `fast=True` marks a metric as cheap/local enough to run under `leg run --fast`
    (see plan.md Phase 3.3) — LLM-judge metrics default to `False`, schema checks to `True`.
    """

    name: str
    threshold: float | None = None
    fast: bool = False


class SuiteConfig(BaseModel):
    # A single dataset path, or several concatenated in order — e.g. the `security` suite spans
    # one JSONL file per attack category (see core/dataset.py's load_dataset_cases).
    dataset: str | list[str]
    metrics: list[MetricConfig]


class JudgeConfig(BaseModel):
    model: str | None = None
    base_url: str | None = None


class LegConfig(BaseModel):
    suites: dict[str, SuiteConfig]
    judge: JudgeConfig = Field(default_factory=JudgeConfig)


def load_config(path: str | Path) -> LegConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no leg config at {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return LegConfig.model_validate(raw)
