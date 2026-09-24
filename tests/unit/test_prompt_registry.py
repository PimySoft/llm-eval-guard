"""Template contract + prompt-drift snapshot tests for prompts/*.j2 — see docs/prompt-testing.md.

Why parametrize over `PROMPTS.names()` rather than hand-writing one test per template: this is a
*contract* suite — the check ("required vars render, stays under budget, matches its snapshot")
should apply uniformly to every template that gets added to `prompts/`, not just the one shipped
today.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import UndefinedError

from llm_eval_guard.prompts import PromptRegistry, assert_matches_snapshot

REPO_ROOT = Path(__file__).parent.parent.parent
PROMPTS = PromptRegistry(REPO_ROOT / "prompts")
SNAPSHOT_DIR = REPO_ROOT / "tests" / "fixtures" / "prompt_snapshots"


@pytest.mark.parametrize("name", PROMPTS.names())
def test_template_renders_with_sample_variables(name: str) -> None:
    template = PROMPTS.load(name)

    rendered = template.render(**template.meta.sample_variables)

    assert rendered.strip()


@pytest.mark.parametrize("name", PROMPTS.names())
def test_template_raises_on_missing_required_variable(name: str) -> None:
    template = PROMPTS.load(name)
    incomplete = dict(template.meta.sample_variables)
    incomplete.pop(template.meta.required_variables[0])

    with pytest.raises(UndefinedError):
        template.render(**incomplete)


@pytest.mark.parametrize("name", PROMPTS.names())
def test_template_stays_under_length_budget(name: str) -> None:
    template = PROMPTS.load(name)
    rendered = template.render(**template.meta.sample_variables)

    if template.meta.max_length is not None:
        assert len(rendered) <= template.meta.max_length


@pytest.mark.parametrize("name", PROMPTS.names())
def test_template_matches_committed_snapshot(name: str, update_snapshots: bool) -> None:
    template = PROMPTS.load(name)
    rendered = template.render(**template.meta.sample_variables)

    assert_matches_snapshot(rendered, SNAPSHOT_DIR / f"{name}.txt", update=update_snapshots)


def test_load_rejects_sample_variables_missing_a_required_variable(tmp_path: Path) -> None:
    (tmp_path / "broken.j2").write_text("{{ greeting }}", encoding="utf-8")
    (tmp_path / "broken.meta.yaml").write_text(
        "version: '1.0'\nrequired_variables: [greeting]\nsample_variables: {}\n",
        encoding="utf-8",
    )
    registry = PromptRegistry(tmp_path)

    with pytest.raises(ValueError, match="greeting"):
        registry.load("broken")
