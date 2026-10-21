"""Covers every branch of prompts/snapshot.py's drift detector directly; test_prompt_registry.py
only exercises the "snapshot exists and matches" path against the committed snapshots."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_eval_guard.prompts import assert_matches_snapshot


def test_missing_snapshot_is_written_then_fails_once(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "prompt.txt"

    with pytest.raises(pytest.fail.Exception, match="no snapshot"):
        assert_matches_snapshot("hello", path, update=False)

    assert path.read_text(encoding="utf-8") == "hello"
    assert_matches_snapshot("hello", path, update=False)  # second run passes


def test_missing_snapshot_with_update_is_written_silently(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"

    assert_matches_snapshot("hello", path, update=True)

    assert path.read_text(encoding="utf-8") == "hello"


def test_drift_fails_with_a_unified_diff(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("Answer only from the context.\n", encoding="utf-8")

    with pytest.raises(pytest.fail.Exception) as excinfo:
        assert_matches_snapshot("Answer the question.\n", path, update=False)

    message = str(excinfo.value)
    assert "-Answer only from the context." in message
    assert "+Answer the question." in message
    assert "--update-snapshots" in message


def test_update_overwrites_a_drifted_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("old", encoding="utf-8")

    assert_matches_snapshot("new", path, update=True)

    assert path.read_text(encoding="utf-8") == "new"
