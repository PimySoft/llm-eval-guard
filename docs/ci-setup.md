# CI Setup

`.github/workflows/ci.yml` — seven jobs, all on GitHub-hosted `ubuntu-latest` runners, $0 cost (see
below). Composite actions in `.github/actions/` dedupe the Poetry/Ollama setup steps shared across
jobs.

## Jobs

- **`changes`** — no matrix, no Ollama needed. `dorny/paths-filter` decides whether
  `schema-drift`/`eval-suite`/`demo-rag`/`security-suite` are worth running.
- **`lint`** — matrixed over Python 3.10/3.11/3.12, no Ollama needed. Runs `ruff check`,
  `ruff format --check`, `mypy`.
- **`unit-tests`** — matrixed over Python 3.10/3.11/3.12, no Ollama needed. Runs `pytest` —
  `live_llm`-marked tests auto-skip without Ollama (`pytest_plugin.py`), so this job stays fast
  and network-free without any marker filtering.
- **`schema-drift`** — no matrix, no Ollama needed. Runs `leg run --fast` — schema validation +
  prompt-drift snapshots, no network calls.
- **`eval-suite`** — no matrix, needs Ollama. Runs `pytest -m live_llm` over the quality-metric
  tests, then `leg run --suite quality --report-dir` for the job-summary report.
- **`demo-rag`** — no matrix, needs Ollama. The demo app (`examples/demo_rag`, generator
  `qwen2.5:0.5b`) answers its questions, then `leg run --suite demo` gates on its exit code
  directly: `context_recall` is deterministic, so no judge and no xfails are involved.
- **`security-suite`** — no matrix, needs Ollama. Same pattern as `eval-suite`, scoped to the
  toxicity + full security-suite live tests.

## Which judge CI runs

- **CI uses the `ci` judge profile** (`qwen2.5:0.5b`, via `LEG_JUDGE_MODEL` + `LEG_JUDGE_PROFILE`):
  a smoke check that the judge plumbing runs end-to-end. It is **not calibrated**.
- **The calibrated judge (`qwen2.5:7b`) doesn't run in CI.** ~15–20 s/case on an M3 GPU means
  well over an hour for the quality suite on a free CPU runner. Gate on it locally or on a
  self-hosted runner: `leg run --suite quality` with the default `judge` block.
- See [judge-calibration.md](judge-calibration.md) for both judges' numbers.

## Why `eval-suite`/`security-suite` gate on pytest, not a raw `leg run` exit code

- **Under the `ci` judge, `leg run`'s exit code is near-random** on judge-scored metrics.
- **The judge-scored integration tests are strict `xfail`s under the `ci` judge**
  (`tests/integration/_judge.py`): green on known judge noise, red on real breakage — and red on
  an unexpected pass, so a changed judge can't slip by unnoticed.
- **`leg run` still runs** (`if: always()`, exit code discarded with `|| true`) — only to produce
  the report.
- **`quality`'s dataset is a calibration set**, half deliberately-bad answers, so `leg run --suite
  quality` exits 1 by design under any judge. Gating on a real system's outputs is `demo-rag`.

## Ollama on the runner

`.github/actions/setup-ollama` installs Ollama, starts it in the background, and pulls the judge
model — cached via `actions/cache` on `~/.ollama` so the model only re-downloads when the tag
changes. No API key, no secret, no cost: it's a free-tier CPU runner running the 0.5B `ci` judge.

## Judge-result cache

`core/cache.py`'s `ResultCache` persists judge-scored `MetricResult`s to `.leg_cache/`, keyed on
`(metric, judge model, threshold, input, output, context)`. `eval-suite`/`security-suite` restore/save that path via
`actions/cache`, keyed on a hash of the relevant dataset files — an unchanged case isn't re-scored
by the judge on the next CI run of the same dataset. This saves CI *time*, not money: the judge is
already $0. `demo-rag` caches the app's answers the same way (`GenerationCache`, keyed on model +
rendered prompt, so a prompt or retriever change regenerates).

## Path-based triggering

The `changes` job (`dorny/paths-filter`) skips `schema-drift`/`eval-suite`/`security-suite` when a
push/PR touches nothing under `llm_eval_guard/`, `datasets/`, `examples/`, `prompts/`, `tests/`, or the Poetry/`leg.config`
files — a docs-only PR doesn't need to spin up Ollama. `lint`/`unit-tests` always run; they're fast
enough that gating them adds more complexity than it saves.

## Reports

`eval-suite`/`demo-rag`/`security-suite` run `leg run --report-dir`, writing `reports/<job>/report.md` +
`report.json`:

- `report.md` is appended to `$GITHUB_STEP_SUMMARY` — visible on the job page, no logs needed.
- `reports/<job>/` is uploaded as a workflow artifact for debugging.
- No PR comment: the job summary covers the same need without a `pull-requests: write` grant.

## Branch protection

To actually block merges on a failing gate, in the repo's GitHub settings → Branches → branch
protection rule for `main`:

1. Enable "Require status checks to pass before merging."
2. Require (at minimum): `lint`, `unit-tests`, `schema-drift`, `eval-suite`, `demo-rag`,
   `security-suite`.
   (Each matrix leg of `lint`/`unit-tests` shows as its own check — require all three Python
   versions, or just one if you want a faster required set with the others as advisory.)
3. Leave "Require branches to be up to date before merging" on if you want re-runs against the
   latest `main` before merge.

## Cost

$0: Actions minutes are free and unlimited for public repos (why the repo stays public), and the
judge is a local Ollama model, never a paid API.

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
