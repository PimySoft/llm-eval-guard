# CI Setup

`.github/workflows/ci.yml`: seven jobs on free `ubuntu-latest` runners. Shared Poetry/Ollama
steps live in composite actions under `.github/actions/`.

## Jobs

No Ollama needed:

- **`changes`** — `dorny/paths-filter`; skips the Ollama jobs and `schema-drift` when a PR touches
  no code, datasets, prompts, tests or Poetry/`leg.config` files (e.g. docs-only)
- **`lint`** (Python 3.10–3.12) — `ruff check`, `ruff format --check`, `mypy`
- **`unit-tests`** (Python 3.10–3.12) — `pytest` under `coverage run`, fails below 80%
  - `live_llm` tests auto-skip without Ollama, so no marker filtering is needed
  - Why not pytest-cov: our `pytest11` entry point imports the package before it starts, so
    module-level lines read as uncovered
- **`schema-drift`** — `leg run --fast`: schema + prompt-drift checks, no network

Need Ollama (uncalibrated `ci` judge, `qwen2.5:0.5b`):

- **`eval-suite`** — `pytest -m live_llm` on quality tests, then `leg run --suite quality` for the report
- **`security-suite`** — same pattern for toxicity + security tests
- **`demo-rag`** — the demo app answers its questions, then `leg run --suite demo` gates on its
  exit code; `context_recall` is deterministic, so no judge is involved

`lint`/`unit-tests` always run. Why: they're fast enough that path-gating them adds more
complexity than it saves.

## The judge in CI

- **CI runs the `ci` judge only** — a plumbing smoke test, not a quality verdict. The calibrated
  `qwen2.5:7b` takes over an hour per suite on a free CPU runner; gate on it locally or
  self-hosted. Both judges' numbers: [judge-calibration.md](judge-calibration.md).
- **`eval-suite`/`security-suite` gate on pytest, not `leg run`'s exit code:**
  - Under the `ci` judge, judge-scored results are near-random.
  - The judge-scored tests are strict `xfail`s under it (`tests/integration/_judge.py`): green on
    known noise, red on real breakage or an unexpected pass.
  - `leg run` still runs (`if: always()`, `|| true`), only to produce the report.
  - `quality`'s dataset is half deliberately-bad answers, so it exits 1 under any judge by design.
- **A judge error fails only its case** (`judge error: …`), never the run; errors aren't cached.

## Caching

- **Ollama model** — `actions/cache` on `~/.ollama`; re-downloads only when the tag changes.
- **Judge results** — `core/cache.py`'s `ResultCache` in `.leg_cache/`, keyed on metric, judge
  model, threshold, input, output and context. CI caches it per dataset hash, so unchanged
  cases aren't re-scored. Saves time, not money.
- **Demo app answers** — `GenerationCache`, keyed on model + rendered prompt, so a prompt or
  retriever change regenerates.

## Reports

`eval-suite`/`demo-rag`/`security-suite` write `reports/<job>/report.md` + `report.json`:

- `report.md` goes into `$GITHUB_STEP_SUMMARY`, visible on the job page.
- `reports/<job>/` is uploaded as a workflow artifact.
- No PR comment. Why: the job summary covers it without a `pull-requests: write` grant.

## Branch protection

In GitHub settings → Branches, add a rule for `main`:

1. Enable "Require status checks to pass before merging."
2. Require `lint`, `unit-tests`, `schema-drift`, `eval-suite`, `demo-rag`, `security-suite`.
   Each Python version of `lint`/`unit-tests` is its own check; require one or all three.
3. Optionally keep "Require branches to be up to date before merging" on.

## Cost

$0: Actions minutes are free for public repos (why the repo stays public), and the judge is a
local Ollama model.

## Release workflow (`.github/workflows/release.yml`)

Triggered by a `vX.Y.Z` tag push, never by merging to `main`.

1. `build` — checks the tag matches `pyproject.toml`'s version, runs `poetry build`, uploads the
   sdist/wheel as an artifact.
2. `publish` — publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/)
   (OIDC), so no API token is stored.

One-time setup before the first tag:

1. On [pypi.org](https://pypi.org/manage/account/publishing/), add a *pending* trusted publisher:
   project `llm-eval-guard`, owner `PimySoft`, repository `llm-eval-guard`, workflow
   `release.yml`, environment `pypi`.
   - Why pending: PyPI can't register a project before its first upload.
2. In GitHub settings → Environments, create `pypi`; optionally add a reviewer so a tag push
   waits for approval.
