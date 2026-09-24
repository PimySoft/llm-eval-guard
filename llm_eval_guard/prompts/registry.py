"""Loads and renders versioned Jinja2 prompt templates from `prompts/*.j2`.

Why a `.meta.yaml` sidecar instead of front-matter inside the `.j2` file: the metadata (version,
required variables, sample inputs) is template *config*, not prompt content — same split as
`datasets/golden/*.jsonl` keeping case data separate from `docs/datasets.md`'s schema docs.
Sidecar YAML is also readable by non-Python tooling without a custom Jinja-comment parser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field


class PromptMeta(BaseModel):
    """Sidecar metadata for one prompt template (`prompts/{name}.meta.yaml`)."""

    version: str
    required_variables: list[str]
    max_length: int | None = None
    sample_variables: dict[str, Any] = Field(default_factory=dict)


class PromptTemplate:
    """A loaded template plus its metadata, ready to render."""

    def __init__(self, name: str, meta: PromptMeta, source: str, env: Environment) -> None:
        self.name = name
        self.meta = meta
        self.source = source
        self._env = env

    def render(self, **variables: Any) -> str:
        """Render the template. Raises `jinja2.UndefinedError` if a required variable is missing —
        `StrictUndefined` (set on the owning `PromptRegistry`'s environment) is what turns a
        forgotten variable into a loud failure instead of a silently blank substitution."""
        return self._env.get_template(f"{self.name}.j2").render(**variables)


class PromptRegistry:
    """Reads `{prompts_dir}/{name}.j2` + `{prompts_dir}/{name}.meta.yaml` pairs."""

    def __init__(self, prompts_dir: str | Path) -> None:
        self._dir = Path(prompts_dir)
        self._env = Environment(
            loader=FileSystemLoader(self._dir),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """Load and cache the `{name}` template. Fails fast if `required_variables` isn't a
        subset of `sample_variables` — that mismatch would otherwise only surface later, as a
        confusing `UndefinedError` from a contract/snapshot test that assumed the sample was
        complete."""
        if name in self._cache:
            return self._cache[name]

        meta_path = self._dir / f"{name}.meta.yaml"
        meta = PromptMeta.model_validate(yaml.safe_load(meta_path.read_text(encoding="utf-8")))
        missing = set(meta.required_variables) - set(meta.sample_variables)
        if missing:
            raise ValueError(
                f"prompts/{name}.meta.yaml: sample_variables is missing required_variables "
                f"{sorted(missing)}"
            )

        source = (self._dir / f"{name}.j2").read_text(encoding="utf-8")
        template = PromptTemplate(name=name, meta=meta, source=source, env=self._env)
        self._cache[name] = template
        return template

    def names(self) -> list[str]:
        """All template names available in this registry's directory."""
        return sorted(p.stem for p in self._dir.glob("*.j2"))

    def render(self, name: str, **variables: Any) -> str:
        return self.load(name).render(**variables)
