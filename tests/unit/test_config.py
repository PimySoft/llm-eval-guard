from __future__ import annotations

from pathlib import Path

import pytest

from llm_eval_guard.core.config import load_config

REPO_CONFIG = Path(__file__).parent.parent.parent / "leg.config.yaml"


def test_load_config_parses_repo_config() -> None:
    config = load_config(REPO_CONFIG)

    assert set(config.suites) == {"quality", "schema", "security"}
    assert config.suites["quality"].dataset == "datasets/golden/sample_rag_qa.jsonl"
    assert config.suites["schema"].metrics[0].fast is True
    assert config.judge.model == "qwen2.5:7b"
    assert config.resolve_judge("ci").model == "qwen2.5:0.5b"


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_load_config_parses_repo_security_suite_multi_dataset() -> None:
    config = load_config(REPO_CONFIG)

    assert "security" in config.suites
    assert isinstance(config.suites["security"].dataset, list)
    assert len(config.suites["security"].dataset) == 4


def test_load_config_defaults_judge_when_omitted(tmp_path: Path) -> None:
    config_path = tmp_path / "leg.config.yaml"
    config_path.write_text(
        "suites:\n  demo:\n    dataset: x.jsonl\n    metrics: []\n", encoding="utf-8"
    )

    config = load_config(config_path)

    assert config.judge.model is None
    assert config.judge.base_url is None


def test_resolve_judge_picks_named_profile_or_default(tmp_path: Path) -> None:
    config_path = tmp_path / "leg.config.yaml"
    config_path.write_text(
        "suites: {}\njudge:\n  model: big\njudge_profiles:\n  ci:\n    model: small\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.resolve_judge(None).model == "big"
    assert config.resolve_judge("ci").model == "small"
    with pytest.raises(ValueError, match="known: ci"):
        config.resolve_judge("nope")
