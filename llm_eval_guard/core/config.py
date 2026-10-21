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
    # `module.path:function` taking and returning an `EvalCase`: the system under test, called
    # per case to fill `actual_output`/`retrieval_context` at run time (e.g. examples/demo_rag).
    generator: str | None = None


class JudgeConfig(BaseModel):
    model: str | None = None
    base_url: str | None = None


class LegConfig(BaseModel):
    suites: dict[str, SuiteConfig]
    # `judge` is the default (calibrated, "recommended") judge; `judge_profiles` holds named
    # alternatives such as a fast `ci` smoke-check judge, picked with `leg run --judge <name>`.
    # Why named profiles over a second config file: the suites/thresholds stay defined once.
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    judge_profiles: dict[str, JudgeConfig] = Field(default_factory=dict)

    def resolve_judge(self, profile: str | None) -> JudgeConfig:
        """``None`` means the default ``judge`` block; anything else must be a declared profile."""
        if profile is None:
            return self.judge
        if profile not in self.judge_profiles:
            known = ", ".join(sorted(self.judge_profiles)) or "none declared"
            raise ValueError(f"unknown judge profile {profile!r} (known: {known})")
        return self.judge_profiles[profile]


def load_config(path: str | Path) -> LegConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no leg config at {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return LegConfig.model_validate(raw)
