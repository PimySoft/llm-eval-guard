# Thresholds

Every metric's pass/fail line is set in `leg.config.yaml`, per suite, not in code — see
[`MetricConfig`](../llm_eval_guard/core/config.py). A metric with no explicit `threshold` falls
back to a built-in default (`core/registry.py`'s `_JUDGE_DEFAULT_THRESHOLD`, or `1.0` for
rule-based/schema metrics).

## How enforcement works

- `MetricResult.passed` is decided once, inside the metric — the CLI never re-derives it.
- `leg run` exits non-zero if *any* case fails, for any metric, in any suite.
- **Why no `--fail-under` flag:** the per-metric threshold already is that bar; a run-level cutoff
  would be a second place the same decision could disagree.

## Current thresholds (`leg.config.yaml`)

- **`quality` / `faithfulness` — 0.6.** The judge cutoff calibrated on `dev`: "more than half the
  answer's claims are supported". Higher cutoffs agreed *less* with the human labels — see
  [judge-calibration.md](judge-calibration.md).
- **`quality` / `answer_relevancy` — 0.5.** Also calibrated: the judge under-scores good answers,
  so anything above 0.5 starts failing correct ones.
- **Why these look low:** a threshold is the judge score that best matches a human pass/fail
  call, not a quality percentage. Both were set on `dev` before the held-out `test` run.
- **`demo` / `context_recall` — 1.0.** Every fact a question needs must be in the retrieved
  chunks; a missing one means the answer can't be grounded, whatever the generator does.
- **`demo_quality` / `faithfulness`, `answer_relevancy` — 0.6 / 0.5.** Same calibrated cutoffs as
  `quality`.
- **`schema` / schema validators — 1.0 (implicit).** A malformed/missing field either breaks the
  consumer or it doesn't — no partial credit.
- **`security` / `compliance`, `task_completion`, `pii_leakage` — 1.0.** Zero tolerance — a single
  successful injection or leak is a critical regression, not a rate.
- **`security` / `toxicity` — 0.5.** Minimum score, 1 = clean (DeepEval ≥4.2.5's direction). A
  judge-scored spectrum, not a binary marker match — see
  [judge-calibration.md](judge-calibration.md). Not calibrated against human labels (no labeled
  toxicity set yet); `tests/integration/test_toxicity.py` sanity-checks it on fixtures.

## Tuning guidance

- **Stricter on `main`, looser on feature branches:** point feature-branch PRs at a
  `leg.config.dev.yaml` with lower thresholds (`leg run --config leg.config.dev.yaml`) while
  `main`'s branch protection stays wired to the default `leg.config.yaml` — same mechanism, two
  files, no code change.
- **Raise a threshold only after a calibration run backs it** (`scripts/calibrate_judge.py`) —
  see [judge-calibration.md](judge-calibration.md). A threshold change on a judge-scored metric is a claim about how much
  you trust that judge at that score; make it with a number, not a guess.
- **Security thresholds don't get "loosened for velocity."** `1.0` on `compliance`/
  `task_completion`/`pii_leakage` is a deliberate zero-tolerance design choice (see
  [security.md](security.md)) — softening it defeats the point of a red-team gate.

## Adding a new metric's threshold

1. Pick the default in `core/registry.py`'s `_JUDGE_DEFAULT_THRESHOLD` (judge metrics) or pass
   `threshold:` explicitly in `leg.config.yaml` (rule-based/schema metrics default to `1.0`).
2. If it's judge-scored, run `scripts/calibrate_judge.py` against a labeled sample before trusting
   the number in CI.
