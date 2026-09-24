# Thresholds

Every metric's pass/fail line is set in `leg.config.yaml`, per suite, not in code — see
[`MetricConfig`](../llm_eval_guard/core/config.py). A metric with no explicit `threshold` falls
back to a built-in default (`core/registry.py`'s `_JUDGE_DEFAULT_THRESHOLD`, or `1.0` for
rule-based/schema metrics).

## How enforcement works

`MetricResult.passed` is decided once, inside the metric itself, against its `threshold` — the
CLI never re-derives pass/fail from a raw score. `leg run` exits non-zero the moment *any* case
in the run fails, for any metric, in any suite (`cli.py`'s `_render_results`). There's no separate
`--fail-under` flag: a per-metric threshold *is* the fail-under bar, already enforced per case —
adding a second, run-level cutoff would just be a second place the same decision could disagree
with the first.

## Current thresholds (`leg.config.yaml`)

- **`quality` / `faithfulness` — 0.8.** A RAG answer citing unsupported claims is a hallucination
  regression, not a matter of degree.
- **`quality` / `answer_relevancy` — 0.8.** Same bar as faithfulness — see [security.md](security.md)
  for why they're scored separately.
- **`schema` / schema validators — 1.0 (implicit).** A malformed/missing field either breaks the
  consumer or it doesn't — no partial credit.
- **`security` / `compliance`, `task_completion`, `pii_leakage` — 1.0.** Zero tolerance — a single
  successful injection or leak is a critical regression, not a rate.
- **`security` / `toxicity` — 0.5.** A judge-scored spectrum, not a binary marker match — see
  [judge-calibration.md](judge-calibration.md) for why this metric's *pass/fail* is still not
  fully trusted at the shipped default judge.

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
