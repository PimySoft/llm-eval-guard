"""Golden-file snapshot testing for rendered prompts — the prompt-drift detector.

Why snapshots instead of just re-asserting the contract test's constraints (required vars render,
under the length budget): those checks pass even if the *wording* silently changes. A snapshot
catches the actual text drifting, so a prompt-engineering edit shows up as a reviewable diff in
the PR instead of a silent behavior change.
"""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest


def assert_matches_snapshot(rendered: str, snapshot_path: Path, *, update: bool) -> None:
    """Compare `rendered` against the golden file at `snapshot_path`.

    - Snapshot missing: write it and fail once, so a new snapshot always gets reviewed and
      committed deliberately rather than silently accepted on first run.
    - `update=True` (`pytest --update-snapshots`): overwrite the snapshot to match `rendered`.
    - Otherwise: fail with a unified diff if the rendered output no longer matches.
    """
    if not snapshot_path.exists():
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(rendered, encoding="utf-8")
        if update:
            return
        pytest.fail(
            f"no snapshot at {snapshot_path} — created it from the current render; "
            "review it and commit it, then re-run"
        )

    if update:
        snapshot_path.write_text(rendered, encoding="utf-8")
        return

    expected = snapshot_path.read_text(encoding="utf-8")
    if rendered != expected:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                rendered.splitlines(),
                fromfile=f"{snapshot_path} (snapshot)",
                tofile="rendered",
                lineterm="",
            )
        )
        pytest.fail(
            f"prompt render drifted from snapshot {snapshot_path}:\n{diff}\n"
            "Run `pytest --update-snapshots` to accept this change, then review and commit the "
            "updated snapshot like a code diff."
        )
