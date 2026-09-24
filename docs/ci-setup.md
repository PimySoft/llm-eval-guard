# CI Setup

`.github/workflows/ci.yml` — six jobs, all on GitHub-hosted `ubuntu-latest` runners, $0 cost (see
below). Composite actions in `.github/actions/` dedupe the Poetry/Ollama setup steps shared across
jobs.

## Jobs

- **`changes`** — no matrix, no Ollama needed. `dorny/paths-filter` decides whether
  `schema-drift`/`eval-suite`/`security-suite` are worth running.
- **`lint`** — matrixed over Python 3.10/3.11/3.12, no Ollama needed. Runs `ruff check`,
  `ruff format --check`, `mypy`.
- **`unit-tests`** — matrixed over Python 3.10/3.11/3.12, no Ollama needed. Runs `pytest` —
  `live_llm`-marked tests auto-skip without Ollama (`pytest_plugin.py`), so this job stays fast
  and network-free without any marker filtering.
- **`schema-drift`** — no matrix, no Ollama needed. Runs `leg run --fast` — schema validation +
  prompt-drift snapshots (Phase 3.3), no network calls.
- **`eval-suite`** — no matrix, needs Ollama. Runs `pytest -m live_llm` over the quality-metric
  tests, then `leg run --suite quality --report-dir` for the job-summary report.
- **`security-suite`** — no matrix, needs Ollama. Same pattern as `eval-suite`, scoped to the
  toxicity + full security-suite live tests.

## Why `eval-suite`/`security-suite` gate on pytest, not a raw `leg run` exit code

The shipped default judge (`qwen2.5:0.5b`) fails its own calibration bar — see
[judge-calibration.md](judge-calibration.md). `leg run --suite quality`'s exit code would
therefore be noisy: near-random pass/fail on cases the judge can't actually discriminate, not a
meaningful signal. `tests/integration/test_faithfulness.py`, `test_answer_relevancy.py`, and the
judge-scored leg of `test_cli_run.py`/`test_toxicity.py` already encode this as
`xfail(strict=False)` (Phase 2.6). Running those through `pytest` in CI keeps the required check
green *unless something other than known judge noise breaks* — a real regression (the plumbing
breaking, an xfail unexpectedly passing under `strict`, etc.) still fails the job. A `leg run`
invocation still runs afterward (`if: always()`) purely to produce the report — its own exit code
is discarded (`|| true`), since gating on it would reintroduce the same noise.

Once a judge model clears calibration (`scripts/calibrate_judge.py --model <bigger model>`), swap
`LEG_JUDGE_MODEL` in the workflow and drop the `xfail` markers — `leg run`'s exit code becomes a
trustworthy gate at that point and the `pytest -m live_llm` steps can be replaced with a direct
`leg run --suite quality` / `--suite security` call.

## Ollama on the runner

`.github/actions/setup-ollama` installs Ollama, starts it in the background, and pulls the judge
model — cached via `actions/cache` on `~/.ollama` so the model only re-downloads when the tag
changes. No API key, no secret, no cost: it's a free-tier CPU runner running a 0.5B model.

## Judge-result cache

`core/cache.py`'s `ResultCache` persists judge-scored `MetricResult`s to `.leg_cache/`, keyed on
`(metric, input, output, context)`. `eval-suite`/`security-suite` restore/save that path via
`actions/cache`, keyed on a hash of the relevant dataset files — an unchanged case isn't re-scored
by the judge on the next CI run of the same dataset. This saves CI *time*, not money: the judge is
already $0.

## Path-based triggering

The `changes` job (`dorny/paths-filter`) skips `schema-drift`/`eval-suite`/`security-suite` when a
push/PR touches nothing under `llm_eval_guard/`, `datasets/`, `tests/`, or the Poetry/`leg.config`
files — a docs-only PR doesn't need to spin up Ollama. `lint`/`unit-tests` always run; they're fast
enough that gating them adds more complexity than it saves.

## Reports

Every `eval-suite`/`security-suite` run writes `reports/<job>/report.md` + `report.json`
(`llm_eval_guard/reporting/`, Phase 5.3) via `leg run --report-dir`. The Markdown file is appended
to `$GITHUB_STEP_SUMMARY` so results are visible on the job's summary page without opening logs;
the full `reports/<job>/` directory (Markdown + JSON) is uploaded as a workflow artifact for
post-hoc debugging. Posting the same summary as a PR comment (`actions/github-script`, deduping
against a prior comment) is listed as optional in plan.md Phase 5.3 and isn't implemented — the
job summary already covers the "visible without opening logs" goal without needing a
`pull-requests: write` permission grant.

## Branch protection

To actually block merges on a failing gate, in the repo's GitHub settings → Branches → branch
protection rule for `main`:

1. Enable "Require status checks to pass before merging."
2. Require (at minimum): `lint`, `unit-tests`, `schema-drift`, `eval-suite`, `security-suite`.
   (Each matrix leg of `lint`/`unit-tests` shows as its own check — require all three Python
   versions, or just one if you want a faster required set with the others as advisory.)
3. Leave "Require branches to be up to date before merging" on if you want re-runs against the
   latest `main` before merge.

## Cost

Everything above runs at $0: GitHub-hosted Actions minutes are free and unlimited for public
repos (see plan.md's cost policy — this is also why the repo stays public), and the judge model is
a local Ollama pull, never a paid API. There is nothing to budget.

## Release workflow (`.github/workflows/release.yml`)

Separate from `ci.yml` — publishing a package is a deliberate, tag-triggered action (`git tag
v0.1.0 && git push --tags`), not a side effect of merging to `main`.

1. `build` job: checks the pushed tag (`vX.Y.Z`) matches `pyproject.toml`'s version, then
   `poetry build`s the sdist/wheel and uploads them as a workflow artifact.
2. `publish` job: downloads that artifact and publishes to PyPI via
   [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token stored
   as a repo secret.

One-time setup before the first tag push:

1. On [pypi.org](https://pypi.org), register `llm-eval-guard` as a project and add this repo +
   `release.yml` as a trusted publisher (Project → Publishing → Add a new publisher).
2. In this repo's GitHub settings → Environments, create a `pypi` environment (matches
   `environment: pypi` in `release.yml`) — optionally add a reviewer/protection rule so a tag
   push doesn't auto-publish without a manual approval.
