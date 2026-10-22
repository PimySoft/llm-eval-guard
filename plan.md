# LLM-Eval-Guard — Implementation Plan

**Project:** LLM-Eval-Guard — a CI/CD quality gate framework for LLM and RAG applications
**Purpose:** Give teams a drop-in test harness that scores LLM/RAG outputs against quality, schema, and security metrics, and fails a pull request when those scores fall below configurable thresholds.

## Audience & goals for this build

This isn't just a working tool — it's a portfolio piece and a learning exercise, so three constraints apply across every phase below:

1. **Recruiter/interviewer legibility.** Assume the reader skims for 5 minutes: clean commit history (one logical change per commit, descriptive messages), a README that states *what QA/testing skill each phase demonstrates* (see Phase 6.1), and a **finished, polished small scope** beats a sprawling unfinished one. Where a step below is genuinely optional (Ragas as second adapter, GitLab CI parity), it's marked *stretch* — do the core path first, end-to-end, before circling back.
2. **Self-education.** Each phase's checklist entries should leave you able to explain *why*, not just *what*. Where it's not obvious from the code, add a one-line "Why" comment or doc note (see Documentation Policy below) — e.g., why faithfulness and answer-relevancy are scored separately, why indirect injection is a distinct threat from direct injection.
3. **Concise documentation.** See policy below — this cuts against the instinct to over-explain, which also serves goal 1 (recruiters don't read long docs).

### Documentation policy (applies to README, docs/*.md, and code comments for the whole project)
- Every doc file: bullet lists over prose, no Markdown tables, no paragraph over ~4 lines, no restating what the code already shows.
- Every non-obvious design choice gets exactly one "Why:" line, not a discussion.
- `docs/` folder stays flat and short — one file per concern (architecture, thresholds, prompt-testing, ci-setup, datasets, judge-calibration). If a file exceeds ~150 lines, split it or cut it.
- README is the single entry point recruiters will actually read — everything else is reference material one click away.

### Cost policy — $0 budget, no exceptions
Everything in this plan must run on free tiers with no credit card required. Concretely:
- **LLM judge calls (the main cost risk):** default to a **local open-source model via Ollama** (shipped default `qwen2.5:0.5b`, small enough for a GitHub-hosted runner; Phase 8 picks a calibrated replacement). DeepEval and Ragas both support pointing at a custom/local LLM endpoint instead of OpenAI — wire that in Phase 2, not a paid API key.
- **DeepEval's Confident AI cloud reporting is opt-in telemetry/dashboard — leave it disabled** (no login, no cloud sync); run everything in local/offline mode.
- **Optional alternative for faster judge calls:** a free-tier hosted API with no card required (e.g., Groq or Google AI Studio's free tier) — usable for local dev if you want faster iteration than Ollama, but CI must not depend on it (rate limits + would break CI for other contributors without a key). Document this as opt-in, never required.
- **PII/toxicity detection:** PII is regex-based (`security/pii.py`); toxicity uses the local Ollama judge via DeepEval's `ToxicityMetric` — no API cost, no heavy ML dependency, keep it that way.
- **CI minutes:** keep the GitHub repo **public** — GitHub-hosted Actions runners are free and unlimited for public repos (private repos have a limited free minute quota). This also serves goal 1 (recruiters need a public repo anyway).
- **GitLab CI parity (Phase 5.5) stays stretch/optional** — GitLab's free tier caps CI minutes/month even on public projects, unlike GitHub; only add it if the free quota is comfortably enough for occasional demo runs.
- **PyPI publish (Phase 6.4):** free, no changes needed.

## How to use this plan

Work through the phases in order — each one builds on artifacts created by the previous phase (dependency configs, fixtures, runner scripts). Every phase ends with a **Definition of Done** you can use as a merge gate for that slice of work. Checkboxes are meant to be checked off incrementally; commit after each sub-section rather than after the whole phase.

---

## Phase 0 — Project Charter & Scope Lock

Small upfront phase to prevent churn later — nail down the shape of the tool before writing code.

- [x] Define the primary interface: a Python package (`llm_eval_guard`) exposing a CLI (`leg run`, `leg init`) plus a pytest plugin entry point
- [x] Decide supported LLM providers for v1: **Ollama (local, free) as the default/required path**; document OpenAI/Anthropic as "bring your own key" adapters for users who want them, never as a requirement to run the test suite
- [x] Decide the evaluation engine: DeepEval vs Ragas vs both behind an adapter interface (recommend: build a thin internal `Metric` interface, implement first with DeepEval; treat Ragas as a **stretch** second adapter added only after the core path works end-to-end — depth on one engine demos better than breadth across two half-finished ones)
- [x] Write a one-page `VISION.md` (or top section of README) capturing: problem statement, target user (ML/platform engineers), non-goals (not a full observability platform, not a hosted product)
- [x] Pick license (recommend Apache-2.0 for OSS tooling with patent grant) and confirm project name availability on PyPI
- [x] Sketch the "Skills Demonstrated" list you'll put in the README (Phase 6.1) now, as a checklist to build toward — e.g., metric-based eval, schema contract testing, prompt regression testing, adversarial/red-team testing, CI quality gates. Keeping this visible early keeps later phases honest about what they need to prove

**Definition of Done:** `VISION.md` committed, license chosen, core architectural decisions (provider abstraction, metric engine) written down so Phase 1+ doesn't re-litigate them.

---

## Phase 1 — Workspace Initialization

Goal: a clean, reproducible, lint-enforced Python workspace that any contributor can bootstrap in under 5 minutes.

### 1.1 Repository setup
- [x] `git init`, create `main` as default branch
- [x] Add `.gitignore` (Python, Poetry, venv, `.env`, IDE folders, `__pycache__`, `.pytest_cache`, `.ruff_cache`, coverage artifacts)
- [x] Create base directory structure:
  ```
  llm_eval_guard/        # source package
    core/                 # metric interfaces, config loader, runner
    metrics/              # faithfulness, relevancy, toxicity, pii, etc.
    schema/                # pydantic validators
    security/              # red-team dataset + injection checks
    reporting/             # markdown/JSON report generators
    cli.py
  tests/
    unit/
    integration/
    fixtures/
  datasets/
    redteam/
    golden/                # golden QA / RAG eval sets
  .github/workflows/
  docs/
  ```
- [x] Add `LICENSE`, empty `README.md` placeholder, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
- [x] Create initial commit

### 1.2 Dependency management
- [x] Choose Poetry (recommended over Pipenv for publishing to PyPI + better lockfile ergonomics) and run `poetry init`
- [x] Pin Python version support range (e.g., `>=3.10,<3.13`) in `pyproject.toml`
- [x] Add core runtime dependencies: `pydantic>=2`, `typer` or `click` (CLI), `pytest`, `rich` (console output)
- [x] Add evaluation dependencies as extras (`poetry add deepeval --group eval` or as optional extras so users can install `llm-eval-guard[ragas]` selectively)
- [x] Add dev-group dependencies: `ruff`, `pre-commit`, `mypy`, `pytest-cov`, `pytest-asyncio`, `pytest-mock`
- [x] Generate `poetry.lock`, commit both files
- [x] Verify `poetry install` works in a clean venv/container

### 1.3 Linting, formatting, type checking
- [x] Configure Ruff in `pyproject.toml` (`[tool.ruff]`): enable `E, F, I, UP, B, SIM` rule sets, set line length, target Python version
- [x] Configure Ruff formatter (replaces Black) — `[tool.ruff.format]`
- [x] Configure `mypy` (`[tool.mypy]`) — strict mode on `llm_eval_guard/`, relaxed on `tests/`
- [x] Add `Makefile` or `justfile` with shortcuts: `make lint`, `make format`, `make typecheck`, `make test`

### 1.4 Pre-commit hooks
- [x] Add `.pre-commit-config.yaml` with hooks: `ruff` (lint + format), `ruff-format`, `mypy` (local hook or mirror), `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`, `detect-private-key`
- [x] Run `pre-commit install` and document it in `CONTRIBUTING.md`
- [x] Run `pre-commit run --all-files` once to confirm a clean baseline

### 1.5 Local dev ergonomics
- [x] Add `.env.example` documenting env vars — `OLLAMA_BASE_URL` (default, required) plus optional/commented-out `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` for the bring-your-own-key path; never commit real `.env`
- [x] Document Ollama install + model pull (`ollama pull llama3.2:3b`) as a prerequisite in README setup, alongside Poetry
- [x] Add `.editorconfig`
- [x] Verify `pytest` runs (even with zero tests) with no config errors

**Definition of Done:** Fresh clone → `poetry install && pre-commit install && make test` succeeds with zero errors on an empty test suite. CI-ready baseline exists (even before Phase 5 wires CI).

---

## Phase 2 — Core Metric Framework

Goal: a pluggable metric interface with faithfulness and answer-relevancy implemented, driven by Pytest fixtures so any team can write `def test_faithfulness(rag_case): assert rag_case.faithfulness_score >= 0.8`.

### 2.1 Metric abstraction layer
- [x] Define `llm_eval_guard/core/metric.py`: abstract `Metric` base class with `name`, `evaluate(input, output, context) -> MetricResult`, `threshold`
- [x] Define `MetricResult` Pydantic model: `score: float`, `passed: bool`, `reason: str | None`, `metric_name: str`
- [x] Define `EvalCase` Pydantic model: `input`, `actual_output`, `expected_output | None`, `retrieval_context | None`, `metadata: dict`
- [x] Write unit tests for the abstract interface using a `FakeMetric` stub

### 2.2 DeepEval integration
- [x] Add adapter `llm_eval_guard/metrics/deepeval_adapter.py` wrapping DeepEval's `FaithfulnessMetric`, `AnswerRelevancyMetric`, `ContextualPrecisionMetric`
- [x] Normalize DeepEval's result object into internal `MetricResult`
- [x] Point the judge model at **Ollama by default** (DeepEval supports a custom/local LLM via its `DeepEvalBaseLLM` interface — wrap the local Ollama model behind that, not `OPENAI_API_KEY`); keep it swappable so a paid provider is opt-in, never required
- [x] Explicitly disable DeepEval's Confident AI cloud login/telemetry (offline/local mode only — no account, no cost)
- [x] Write integration test using a mocked/stubbed judge LLM response (avoid real API/Ollama calls in unit tests — gate live-model tests behind a marker so CI doesn't need Ollama installed on every job)

### 2.3 Ragas integration (secondary adapter — stretch, after 2.2 works end-to-end)
- [ ] Add adapter `llm_eval_guard/metrics/ragas_adapter.py` for `faithfulness`, `answer_relevancy`, `context_recall`
- [ ] Normalize Ragas dataset format (HuggingFace `Dataset`) to/from `EvalCase`
- [ ] Wire Ragas's LLM wrapper to the same local Ollama model (Ragas accepts any LangChain-compatible LLM) — same $0-cost rule as 2.2
- [ ] Document in code which adapter is "default" vs opt-in (avoid double-installing heavy deps by default)

*Deferred — DeepEval path (2.1–2.2) is complete end-to-end; not picked up per the stretch-goal ordering in this plan's audience/goals section.*

### 2.4 Custom Pytest fixtures
- [x] Create `tests/conftest.py` with fixtures: `eval_client` (LLM client under test), `judge_llm` (evaluator model), `golden_dataset` (loads from `datasets/golden/*.jsonl`)
- [x] Create a `pytest` plugin entry point (`llm_eval_guard.pytest_plugin`) exposing fixtures to any downstream repo that installs this package
- [x] Add custom `pytest.mark.eval_metric(name, threshold)` marker for declarative threshold assertions
- [x] Write example test suite in `tests/integration/test_faithfulness.py` and `test_answer_relevancy.py` demonstrating fixture usage end-to-end against a sample golden dataset

### 2.5 Golden dataset seed
- [x] Create `datasets/golden/sample_rag_qa.jsonl` with 10–20 hand-written Q/A/context triples covering easy, ambiguous, and adversarial-but-benign cases
- [x] For each case, add a **hand-assigned human label**: `human_faithfulness` and `human_relevancy` scores (or pass/fail), reasoned through yourself as if you were the judge — this labeled set is what Phase 2.6 calibrates against
- [x] Document the dataset schema in `docs/datasets.md`

### 2.6 Judge calibration (meta-evaluation)
*This is the step that proves you understand evaluation, not just test plumbing: an LLM-judge is itself an unverified component until you check it against ground truth.*
- [x] Write `scripts/calibrate_judge.py` (or a `pytest` case marked `@pytest.mark.calibration`): run the local-Ollama judge (Phase 2.2) over every case in `datasets/golden/sample_rag_qa.jsonl` and compare its scores to the `human_*` labels
- [x] Compute simple agreement metrics — exact/near-match rate for pass/fail, and correlation (Pearson or Spearman) or mean absolute error for numeric scores; no need for anything fancier than `scipy.stats` or a hand-rolled calculation
- [x] Set an explicit **minimum agreement threshold** (e.g., ≥80% pass/fail agreement) and fail the calibration check if the judge falls below it — this is what stops you from silently trusting a bad judge
- [x] Re-run calibration whenever you change the judge model or prompt (e.g., swapping `llama3.2:3b` for `phi3:mini`) — note in `docs/datasets.md` that model choice is a tuning decision backed by this number, not a guess
- [x] Write `docs/judge-calibration.md` (short — see documentation policy): what was measured, the agreement score achieved, and known failure modes (e.g., "judge over-scores verbose answers", if you observe that) — this doc is the artifact you'd point an interviewer to

**Definition of Done:** `pytest tests/integration/test_faithfulness.py -m eval_metric` runs against the sample golden dataset and produces pass/fail results with numeric scores, using a mockable judge LLM for CI-safe execution; separately, the calibration check reports a concrete agreement number between the automated judge and your human labels, and that number is documented. ✅ Met — `tests/integration/test_deepeval_adapter.py` is the CI-safe mocked path (no network calls); `scripts/calibrate_judge.py` measured the default judge (`qwen2.5:0.5b`) at 40%/20% pass/fail agreement — below the 80% bar — documented in `docs/judge-calibration.md` with concrete failure-mode examples, and the live example suite is honestly marked `xfail` against that finding rather than asserting a dishonestly low bar or silently passing.

---

## Phase 3 — Schema & Prompt Drift Validation

Goal: catch structural regressions (broken JSON output, missing fields) and prompt-template regressions before they reach production, with a local runner for pre-commit benchmarking.

### 3.1 Pydantic output schemas
- [x] Define example strict output schemas in `llm_eval_guard/schema/` (e.g., `RagAnswer`, `ToolCallOutput`) demonstrating the pattern consumers should follow
- [x] Add a generic `SchemaValidationMetric` that takes any user-supplied Pydantic model and validates LLM JSON output against it, capturing `ValidationError` details in `MetricResult.reason`
- [x] Support both strict mode (fail on any extra/missing field) and lenient mode (warn only) via config
- [x] Write unit tests: valid payload passes, malformed JSON fails gracefully (no crash), missing required field fails with a clear diff-style message

### 3.2 Prompt template testing
- [x] Choose/standardize a prompt templating approach (e.g., Jinja2 templates stored in `prompts/*.j2`, versioned in git)
- [x] Build a `PromptRegistry` loader that reads templates + metadata (expected variables, version tag)
- [x] Write a "template contract" test suite: for each template, assert required variables render without `UndefinedError`, and rendered output stays under token/length budgets
- [x] Add a **prompt drift detector**: snapshot-test each rendered prompt (golden file per template+inputs pair) and fail the test if the rendered output changes unexpectedly, requiring explicit snapshot update (`--update-snapshots` flag) — this is what catches silent prompt regressions
- [x] Document snapshot review workflow in `docs/prompt-testing.md` (a snapshot diff in a PR should be reviewed like a code diff)

### 3.3 Local evaluation runner (pre-commit benchmark)
- [x] Build `llm_eval_guard/cli.py` command: `leg run --suite <name> --config leg.config.yaml`
- [x] Support a `leg.config.yaml` at repo root defining: which metrics run, thresholds per metric, which datasets to use, judge model config
- [x] Runner outputs a console summary (via `rich`) with pass/fail table and aggregate score
- [x] Add `leg run --fast` mode that skips expensive LLM-judge metrics and only runs schema/prompt-drift checks (cheap enough to run on every commit)
- [x] Wire optional local pre-commit hook entry (`.pre-commit-config.yaml` local hook) so `leg run --fast` executes automatically before commit — no keys or paid services involved, so this is safe to enable by default (mark opt-in only if it feels slow, not because of cost)
- [x] Write a `leg run --help` output test to lock in CLI UX

**Definition of Done:** A developer can run `leg run --fast` locally in under 10 seconds with no network calls, catching schema breaks and prompt drift before ever opening a PR; `leg run` (full suite) exercises real/mocked metric evaluation end-to-end. ✅ Met — `leg run --fast` runs the config-driven `schema` suite (5 clean `ToolCallOutput` cases) in well under a second with zero network calls; `leg run --suite quality` exercises the real DeepEval/Ollama path end-to-end (`tests/integration/test_cli_run.py`, `live_llm`-marked, auto-skips without Ollama like the Phase 2 integration tests). Schema failure-mode behavior (strict fail / lenient warn / malformed-JSON) is proven in isolated `tmp_path` fixtures in `tests/unit/test_schema_validation.py` and `tests/unit/test_cli.py`, kept out of the repo's own dogfood `leg.config.yaml` so the pre-commit `leg-fast` hook stays green. Prompt-drift snapshot testing (3.2) is a plain `pytest`/snapshot mechanism, not a `Metric`/`EvalCase` check — see the scope note in `docs/prompt-testing.md` — so it's already covered by the normal (network-free) `pytest`/pre-commit run rather than by `leg run` itself.

---

## Phase 4 — Security & Red-Teaming Module

Goal: adversarial test coverage for prompt injection, jailbreaks, toxicity, and PII leakage, runnable as its own gated suite.

### 4.1 Red-team dataset construction
- [x] Create `datasets/redteam/prompt_injection.jsonl` — direct injection payloads ("ignore previous instructions...")
- [x] Create `datasets/redteam/indirect_injection.jsonl` — payloads embedded in retrieved/tool-returned content (simulating a poisoned document/webpage the RAG pipeline retrieves)
- [x] Create `datasets/redteam/jailbreak.jsonl` — role-play/DAN-style bypass attempts (curate from public research datasets where licensing permits; cite sources)
- [x] Create `datasets/redteam/pii_leakage.jsonl` — prompts designed to elicit memorized or injected PII (synthetic PII only, never real)
- [x] Document dataset provenance and licensing in `datasets/redteam/README.md`
- [x] Tag each entry with `attack_category`, `severity`, `expected_behavior` (e.g., "must refuse", "must not leak system prompt")

### 4.2 Indirect prompt injection test harness
- [x] Build `llm_eval_guard/security/injection.py`: simulates RAG retrieval returning a poisoned document, then asserts the model's final output does not comply with the embedded instruction
- [x] Implement a `ComplianceMetric` (did the model follow the injected instruction — bad) vs `TaskCompletionMetric` (did it still answer the real user question — good), scored via LLM-judge or rule-based keyword/regex heuristics as a cheaper fallback
- [x] Write tests covering: injected instruction to leak system prompt, injected instruction to change output format, injected instruction to perform an unrelated "action" (simulating tool-calling abuse)

### 4.3 Toxicity checks
- [x] Integrate a toxicity classifier (DeepEval's `ToxicityMetric`, or a lightweight local model like `detoxify` as a fallback to avoid extra API cost)
- [x] Add `ToxicityMetric` adapter with configurable threshold
- [x] Write tests asserting benign outputs score low and known-toxic fixture outputs score high (sanity-check the detector itself)

### 4.4 PII leakage checks
- [x] Integrate a PII detector (e.g., Microsoft Presidio, or regex-based fallback for emails/phones/SSNs/credit cards)
- [x] Add `PIILeakageMetric` that scans model output for PII patterns not present in the input context (distinguishing "echoed user-provided PII" from "leaked/hallucinated PII")
- [x] Write tests with synthetic PII fixtures (never real personal data) covering false-positive edge cases (e.g., example emails like `user@example.com` should not always trigger)

### 4.5 Red-team suite wiring
- [x] Add `leg run --suite security` CLI target that runs only the security/red-team suite
- [x] Define severity-based thresholds in `leg.config.yaml` (e.g., zero tolerance for "must refuse" category, softer threshold for toxicity score)
- [x] Ensure red-team suite results are clearly separated in reporting from quality metrics (security failures should be visually/semantically distinct — treat as blocking by default)

**Definition of Done:** `leg run --suite security` executes the full red-team dataset against a target model/pipeline and produces a pass/fail verdict per attack category, with indirect injection, toxicity, and PII checks all demonstrated against both a known-vulnerable stub model and a known-safe stub model (to prove the detectors actually discriminate). ✅ Met — `leg run --suite security` runs compliance/task_completion/pii_leakage (rule-based, fast) and toxicity (real Ollama judge) against all four `datasets/redteam/*.jsonl` files, passing 68/68 end to end (`tests/integration/test_cli_run.py::test_run_security_suite_end_to_end`, `xfail(strict=False)` for the same known-judge-calibration reason as the Phase 2 quality tests). The shipped datasets model a *defended* pipeline (kept all-passing, same convention as `datasets/golden/`); `tests/unit/test_injection.py` and `test_pii.py` build "vulnerable" variants in-process (`case.model_copy`) and assert each metric catches them — the known-vulnerable-vs-known-safe discrimination the DoD asks for, done without a live model call (see `datasets/redteam/README.md` for why). CLI output renders security failures as `SECURITY FAIL (<severity>)` plus a closing "N security finding(s) — blocking by default" line, distinct from quality/schema `fail`. Full architecture/rationale in `docs/security.md`.

---

## Phase 5 — CI/CD Pipeline Integration

Goal: automated, threshold-enforced gating on every PR, with human-readable reporting.

### 5.1 GitHub Actions workflow
- [x] Create `.github/workflows/ci.yml` with jobs: `lint` (ruff + mypy), `unit-tests` (fast, no model calls), `eval-suite` (metric framework against local Ollama), `security-suite` (red-team), `schema-drift` (Phase 3 checks)
- [x] Use a matrix strategy for Python versions (e.g., 3.10, 3.11, 3.12) on the lint/unit job
- [x] Cache Poetry dependencies (`actions/cache` keyed on `poetry.lock` hash) to keep CI fast
- [x] Install Ollama on the runner and cache the pulled model (`actions/cache` on `~/.ollama`) so the `eval-suite`/`security-suite` jobs run the real local judge model with $0 cost and no secrets required
- [x] No API keys needed for the required path — if the optional bring-your-own-key adapter is ever exercised in CI, gate it behind a repo secret and skip it entirely on forked-repo PRs (never expose a paid key to untrusted PR code) — n/a for now: no CI job exercises the bring-your-own-key adapters at all, so there's no secret to scope yet; noted here for when one is added

### 5.2 Threshold enforcement
- [x] Wire `leg run --config leg.config.yaml --fail-under` to exit non-zero when any metric or security check falls below its configured threshold — no separate `--fail-under` flag was added: `MetricResult.passed` already resolves each case against its `leg.config.yaml` threshold, and `leg run` already exits non-zero the moment any case fails (`cli.py`), so a second run-level cutoff would just be a second place the same decision could disagree with the first — see `docs/thresholds.md`'s "How enforcement works"
- [x] Ensure exit code propagates correctly to the GitHub Actions job (job fails → PR check fails → merge blocked if branch protection requires it)
- [x] Add a `docs/thresholds.md` explaining how to tune thresholds per project maturity (e.g., stricter on `main`, looser on feature branches)
- [x] Document required branch protection setup (require the `eval-suite` and `security-suite` checks to pass before merge) in `docs/ci-setup.md`

### 5.3 Reporting
- [x] Build `llm_eval_guard/reporting/markdown_report.py` generating a Markdown summary: overall pass/fail, per-metric score table, top failing cases with diffs, security findings by severity
- [x] Wire the report into GitHub Actions Job Summary (`$GITHUB_STEP_SUMMARY`) so results are visible without opening logs
- [ ] Optionally post the same summary as a PR comment via `actions/github-script` or a small composite action (dedupe/update existing comment rather than spamming new ones on each push) — *stretch, left undone*: plan.md marks this "optional," and the job summary (above) already meets the "visible without opening logs" goal without a `pull-requests: write` permission grant — see `docs/ci-setup.md`
- [x] Emit a machine-readable JSON report alongside Markdown (for future dashboarding/trend tracking)
- [x] Upload full report + raw eval traces as a workflow artifact for debugging failed runs

### 5.4 Performance & cost controls
- [x] Add caching for LLM-judge calls keyed on `(input, output, metric)` hash to avoid re-running the local model on unchanged cases across CI re-runs (saves CI *time*, not money, since the model is free — but still worth it for speed)
- [x] Add a `paths-filter` or path-based trigger so the full eval/security suite only runs when relevant files change (prompts, source, datasets), not on doc-only PRs
- [x] Note in `docs/ci-setup.md` that the whole pipeline runs at $0 — local model, free GitHub Actions minutes (public repo) — so there's nothing to budget

### 5.5 GitLab CI parity (skip unless specifically wanted)
- [ ] Lowest priority item in the whole plan — GitHub Actions alone is enough to demonstrate the CI-gating skill, and GitLab's free tier has a monthly CI-minute cap (unlike GitHub's unlimited public-repo minutes). Only build this if you specifically want GitLab experience on your resume; otherwise leave unchecked and move on

**Definition of Done:** Opening a PR against `main` in a test repo triggers all CI jobs, a failing metric or security check blocks merge via required status checks, and the PR shows a Markdown summary table of results without needing to open raw logs. ✅ Met — `.github/workflows/ci.yml` runs `lint`/`unit-tests` (matrixed over Python 3.10–3.12) unconditionally, and `schema-drift`/`eval-suite`/`security-suite` when `dorny/paths-filter` detects a relevant path changed; each of the latter three writes `reports/<job>/report.md` into `$GITHUB_STEP_SUMMARY` and uploads `report.md`+`report.json` as a workflow artifact. `eval-suite`/`security-suite` gate on `pytest -m live_llm` rather than a raw `leg run` exit code — a deliberate call, not an oversight, because the shipped default judge fails its own calibration bar (Phase 2.6); see `docs/ci-setup.md` for the full rationale and the swap-over path once a calibrated judge is in place. Judge-result caching (`core/cache.py`, wired into `core/runner.py` and `leg run --cache/--no-cache`) and `leg run --report-dir` (`llm_eval_guard/reporting/`) are both unit-tested (`tests/unit/test_cache.py`, `test_reporting.py`, `test_cli.py`) without any live model call, consistent with the Cost policy's mock-the-judge-in-unit-tests rule.

---

## Phase 6 — Documentation & Maintenance

Goal: a README and docs set that lets a new adopter go from zero to a working quality gate in under 15 minutes.

### 6.1 README.md
- [x] Write project tagline + badges (build status, PyPI version, license, code style)
- [x] "Why LLM-Eval-Guard" section — problem statement, comparison to raw DeepEval/Ragas (what this framework adds: CI wiring, schema drift, security suite, reporting)
- [x] **"Skills Demonstrated" table** — the recruiter-facing anchor of the README. One row per QA competency, linking straight to the code that proves it, e.g.:

  | Skill | Where |
  |---|---|
  | Metric-based LLM/RAG eval | `llm_eval_guard/metrics/`, Phase 2 |
  | Judge calibration (meta-evaluation vs. human labels) | `docs/judge-calibration.md`, Phase 2.6 |
  | Schema/contract testing | `llm_eval_guard/schema/`, Phase 3.1 |
  | Regression testing (prompt drift via snapshots) | `llm_eval_guard/schema/` prompt tests, Phase 3.2 |
  | Adversarial/security testing (prompt injection, PII, toxicity) | `llm_eval_guard/security/`, Phase 4 |
  | CI quality gates & automated reporting | `.github/workflows/ci.yml`, Phase 5 |

- [x] Quickstart: `pip install llm-eval-guard`, `leg init` (scaffolds `leg.config.yaml` + example tests), `leg run`
- [x] Configuration reference table for `leg.config.yaml` keys
- [x] Usage examples: adding a custom metric, adding a custom red-team dataset entry, wiring a new LLM provider adapter
- [x] CI badge + snippet showing the GitHub Actions job summary output (screenshot or embedded example)
- [x] Keep the whole file scannable in under 3 minutes — this is the one doc a recruiter actually opens; push anything else to `docs/`

### 6.2 Architecture documentation
- [x] Create `docs/architecture.md` with a diagram (Mermaid, embeddable in Markdown/GitHub) showing: EvalCase → Metric adapters (DeepEval/Ragas) → Runner → Reporting → CI gate
- [x] Document the plugin/extension points explicitly (custom `Metric`, custom `PromptRegistry` source, custom PII/toxicity backend) so contributors know where to extend without forking core
- [x] Add a sequence diagram for the indirect-injection test flow (Phase 4.2) since it's the least obvious mechanism

### 6.3 Contributor & maintenance docs
*Keep this section lightweight — it's a solo portfolio project, not a project expecting external contributors yet. Do it for the OSS-hygiene signal, but each file should be short.*
- [x] `CONTRIBUTING.md`: dev setup (references Phase 1), how to add a new metric adapter, one-line ethics note on adding adversarial red-team content
- [x] `SECURITY.md` with a short vulnerability disclosure note (signals security awareness — relevant since this is a security-adjacent tool)
- [ ] Skip issue/PR templates for v0.1 unless you're specifically showcasing repo-governance skills — low signal relative to the docs effort *(intentionally skipped, per this line's own guidance)*
- [x] `CHANGELOG.md` seeded with `v0.1.0`, Keep-a-Changelog format, one line per phase shipped

### 6.4 Release readiness
- [x] Configure `pyproject.toml` package metadata for PyPI publish (description, keywords, classifiers, project URLs)
- [x] Add a release workflow (`.github/workflows/release.yml`) triggered on git tags, building + publishing to PyPI via trusted publishing (OIDC, no long-lived token)
- [x] Tag and cut `v0.1.0` once Phases 1–5 are complete and README quickstart has been manually verified end-to-end on a clean machine/container — *done in Phase 11, so the release includes Phases 7–10*

**Definition of Done:** A new user with no prior context can clone the repo, follow only the README, and get a passing `leg run` against the sample golden dataset within 15 minutes; architecture diagram accurately reflects the shipped code; `v0.1.0` is tagged and published. **Partially met** — `leg init` scaffolds a config + sample dataset + example test that `leg run --fast` passes immediately with zero network calls (verified end-to-end by `tests/unit/test_cli.py::test_init_scaffolds_a_runnable_project`); the scaffolded `tests/test_llm_eval_guard_example.py` plus `ollama pull qwen2.5:0.5b` gets a new user to a real judge-scored `leg run` too, same live-Ollama dependency the rest of the suite already has. `docs/architecture.md` reflects the shipped code. The repo is public at [PimySoft/llm-eval-guard](https://github.com/PimySoft/llm-eval-guard); tagging and publishing `v0.1.0` moved to Phase 11.

---

## Phase 7 — Golden Dataset Expansion

Goal: a labeled set big and balanced enough that a calibration number means something — n=15 can't distinguish a good judge from a lucky one.

- [x] Grow `datasets/golden/sample_rag_qa.jsonl` to ≥50 cases, roughly half that a correct judge should fail (hallucinated detail, unsupported claim, off-topic answer, partially grounded answer)
- [x] Tag every case with a `failure_mode` category (or `none`) so calibration can report per-category agreement, not just a single average
- [x] Split into `dev` and `test` (e.g., 70/30 via a `split` metadata field) — Why: Phase 8 picks a judge model on `dev`; reporting agreement on that same data would overstate it
- [x] Re-label a random 20% of cases a few days later without looking at the first labels; report your own self-agreement in `docs/datasets.md` — Why: the human labels are the ground truth, so their consistency caps how good any judge can look
  - Tooling done (`scripts/relabel_sample.py sample|score`, `llm_eval_guard/core/relabel.py`); the re-label pass itself is a human step, still pending
- [x] Extend `tests/unit/test_dataset.py` to enforce the new fields and the pass/fail balance

**Definition of Done:** ≥50 labeled cases with failure-mode tags and a dev/test split; self-agreement number documented; dataset unit tests enforce the schema. **Met** — 56 cases (28/28 pass/fail, 39 dev / 17 test) with failure-mode tags, enforced by `tests/unit/test_dataset.py`; the 41 new labels were drafted by Claude and reviewed/accepted by the maintainer; self-agreement measured in Phase 13 (kappa 0.25 faithfulness / 0.00 relevancy, n=12, `docs/datasets.md`).

---

## Phase 8 — Calibrated Judge

Goal: turn "the default judge fails calibration" into "this judge passes calibration, and here's the number" — so the quality gate actually gates.

- [x] Extend `scripts/calibrate_judge.py`: `--split dev|test`, per-`failure_mode` agreement, wall-clock seconds per case, and a bootstrap 95% confidence interval on agreement — Why: the interval shows when a difference between two models is just noise
- [x] Run candidate local models on `dev` (e.g., `llama3.2:3b`, `qwen2.5:3b`, `phi3:mini`, `qwen2.5:7b` if hardware allows); record agreement/MAE/r/runtime per model in `docs/judge-calibration.md`
- [x] Pick the best model that clears the ≥80% bar on `dev`, then report its `test`-split numbers once, as the headline result
- [x] If it's too slow for a free CI runner, separate the two roles explicitly: a `ci` judge (fast, documented as a smoke check) and a `recommended` judge (calibrated, for local/self-hosted gating) via `leg.config.yaml`, and say which is which in the docs
- [x] Remove the `xfail` markers that the calibrated judge now passes; make any remaining ones `strict=True` so an unexpected pass fails loudly
- [x] Follow the swap-over path in `docs/ci-setup.md`: switch `eval-suite` from `pytest -m live_llm` to gating on the `leg run` exit code, if the calibrated judge runs in CI
  - Not applicable: the calibrated judge is too slow for a free runner, so CI runs the `ci` judge and stays gated on pytest (see `docs/ci-setup.md`)
- [x] If no local model clears the bar, document that as the finding (with the per-model numbers) and gate on the best one with a lowered, explicitly justified bar — don't quietly pretend

**Definition of Done:** `docs/judge-calibration.md` shows a model comparison and a held-out `test`-split agreement ≥80% with a confidence interval (or a documented, numbers-backed explanation of why none got there); no non-strict `xfail` remains; CI gates on the judge that the docs say it does. **Met via the documented fallback** — six local judges compared on `dev`; `qwen2.5:7b` with per-metric cutoffs (0.6/0.5) fixed on `dev` before one `test` run: relevancy 82% [59–100%], faithfulness 71% [47–88%]. Faithfulness is gated at a lowered, justified 70% bar (`docs/judge-calibration.md`). Roles split: `qwen2.5:7b` is the default/recommended judge, `qwen2.5:0.5b` the `ci` profile CI runs; judge-scored tests are strict `xfail`s only under the `ci` judge (verified in two live runs). No non-strict `xfail` remains. Also fixed: the judge cache ignored model/threshold.

---

## Phase 9 — System Under Test: Demo RAG App + Caught Regression

Goal: prove the gate catches a real regression in a real (tiny) system, rather than scoring hand-written outputs.

- [x] Add `examples/demo_rag/`: a few markdown docs, a simple retriever with no new heavy dependency (keyword/BM25), and generation through the local Ollama model using the `prompts/rag_answer.j2` template
- [x] Add a `leg` suite whose `actual_output`/`retrieval_context` are *generated* by the demo app at test time (cache them via `core/cache.py`), not hard-coded
- [x] Run the red-team datasets against the demo app's real responses too; record which attacks it actually fell for in `docs/security.md` — a real finding is worth more than a clean sheet
- [x] Create the regression demo: a branch that makes one realistic bad change (e.g., the prompt drops "answer only from the context", or the retriever returns top-1 instead of top-3), open a PR, and let CI go red. Keep the PR closed-unmerged and link it from the README with a screenshot of the job summary
- [x] Write `docs/test-strategy.md` (short): risk list for an LLM/RAG feature → which check covers each risk → what is deliberately *not* covered and why — Why: it shows test planning and prioritisation, not just tooling

**Definition of Done:** a linked, red PR in the public repo where the gate caught a deliberately introduced regression in the demo app; the red-team results for the demo app are documented; `docs/test-strategy.md` exists. **Met** — demo app in `examples/demo_rag/` (4 docs / 16 chunks, BM25 top-3, `qwen2.5:3b` via Ollama, generations cached by `core/cache.py`'s `GenerationCache`). Suites take a `generator:` hook; the `demo` suite (deterministic `context_recall`) gates CI's `demo-rag` job on its exit code, `demo_quality` scores the answers with the judge. `demo_security` runs the red-team sets through the app: it fell for 5 of 17 attacks; the gate caught 2, missed 3, and raised 1 false alarm (`docs/security.md`). `docs/test-strategy.md` maps risks to checks and lists what is deliberately not covered. Regression demo: [PR #2](https://github.com/PimySoft/llm-eval-guard/pull/2) (`TOP_K` 3 → 1, open, never merged) turns CI's `demo-rag` gate red — `context_recall` 12/12 → 8/12 — while the calibrated judge only moves 20/24 → 19/24; linked from the README with the job-summary screenshot.

---

## Phase 10 — Security & Test-Suite Hardening

Goal: close the specific weaknesses a careful reviewer would spot in the rule-based checks and the test suite.

- [x] PII (`security/pii.py`): add UK National Insurance number, UK phone number, UK postcode, and IBAN patterns; add a Luhn check to `credit_card` to cut false positives on arbitrary 16-digit numbers; synthetic test data only (see CONTRIBUTING.md)
- [x] Injection (`security/injection.py`): add unit cases for the known false positive (a refusal that quotes the attack, e.g. "I won't wire $500") and false negative (paraphrased compliance); mitigate the false positive (e.g., don't count markers inside quoted spans or immediately after a refusal phrase) and document the remaining limits in `docs/security.md`
- [x] Make every remaining `xfail` `strict=True`, and set `asyncio_default_fixture_loop_scope` to clear the pytest deprecation warnings
- [x] Raise unit coverage from 67% to ≥80%; add `--cov-fail-under=80` to the `unit-tests` CI job

**Definition of Done:** new PII patterns plus the Luhn check are unit-tested; the injection false positive/negative cases exist and the mitigated one passes; there are no non-strict `xfail`s and no deprecation warnings; CI enforces ≥80% coverage. **Met** — PII: UK NINO/phone/postcode and IBAN patterns, Luhn on cards, mod-97 on IBANs, formatting-insensitive echo matching; all unit-tested on synthetic values (Ofcom drama numbers, documentation IBAN, card test numbers). Injection: compliance markers inside quotes or after a same-clause refusal no longer count (4 refusal FP cases pass; would fail on the old matcher); demo-app verdicts unchanged at 63/68; the paraphrase FN and `as dan` persona-echo FP are strict `xfail`s with limits in `docs/security.md`. Warnings: every `xfail` was already strict, now enforced by `xfail_strict = true`; `asyncio_default_fixture_loop_scope` set (also in `pytester` inner runs); DeepEval's toxicity "direction flipped" notice silenced at the call site after confirming our 0.5 is already a minimum score; a deprecation raised from `llm_eval_guard` code now fails the test run. Zero warnings in the unit run and the live toxicity run. Coverage: the 67% was a measurement artifact — the `pytest11` entry point imports the package before pytest-cov starts, so module-level lines read as missed; measured with `coverage run -m pytest` it was already 96%. Swapped pytest-cov for `coverage[toml]`, added tests for the snapshot drift detector and `assert_min_pass_rate` (now 98%), and the `unit-tests` job fails below 80% (`fail_under` in `pyproject.toml`, also `make cov`). Also fixed a circular import that broke `import llm_eval_guard.security` as a first import.

---

## Phase 11 — Release v0.1.0

Goal: ship it. This replaces the outstanding Phase 6.4 tag step, so the published version includes Phases 7–10.

- [x] Fix the Phase 6 DoD note that says the repo has no GitHub remote (it now has one); make sure the repo is public
- [x] Register the PyPI trusted publisher (one-time setup, see the "Release workflow" section of `docs/ci-setup.md`)
- [x] Verify the README quickstart end-to-end in a clean container (`pip install` from TestPyPI or a built wheel → `leg init` → `leg run --fast`)
- [x] Update `CHANGELOG.md` with Phases 7–10, then `git tag v0.1.0 && git push --tags` — a manual, human step
- [x] Confirm the PyPI page renders and the PyPI badge in the README resolves
  - Page renders, but the README's relative links and screenshot broke there; now absolute URLs, visible on PyPI from the next release

**Definition of Done:** `pip install llm-eval-guard` works from public PyPI on a clean machine, and the README quickstart passes as written. **Met** — the quickstart passes as written from a built wheel in a clean `python:3.10-slim` container: `leg init` scaffolds, `leg run --fast` scores 1/1 with no network call, and the scaffolded pytest example auto-skips without Ollama. The check found three bugs, now fixed: the scaffolded suite had no fast metric, so `--fast` evaluated nothing and "passed"; `leg --help` printed an internal developer note; and the unquoted `[deepeval]` extra fails under zsh. PyPI pending trusted publisher and the GitHub `pypi` environment are set up. `v0.1.0` tagged and published to PyPI (wheel + sdist, trusted publishing); `pip install "llm-eval-guard[deepeval]"` → `leg init` → `leg run --fast` gives 1/1 passed in a clean container from public PyPI; the PyPI badge resolves.

---

## Phases 12–18 — Portfolio Hardening

Source: a hiring-manager review of the repo (QA role, RAG testing one skill of many). It flagged:

- Most commits are AI co-authored, so the maintainer must be able to defend every decision unaided
- The labels come from one person, and their self-agreement hasn't been measured
- The held-out set is small (n=17)
- Injection detection is keyword-based, so a paraphrase gets past it
- No system the maintainer didn't build has been tested
- There's no answer for production scale or multi-turn conversations
- The repo shows nothing of the conventional QA stack

Two kinds of work:

- **Code phases** follow the normal workflow: one commit per sub-item, plan.md tick, CHANGELOG entry.
- **Study material** lives in `study/` at the repo root, one file per topic.
  - Why not `docs/`: `docs/` is for users of the tool; `study/` is for the maintainer learning it.
  - Not shipped in the package.
  - Each file ends with self-check questions, with answers in a collapsed `<details>` block.
  - The documentation policy applies here too.
- Every phase that adds code also adds or updates a `study/` note, so the learning keeps pace with the code.

---

## Phase 12 — Study Guides: Own the Existing Code

Goal: be able to explain and defend every design decision in Phases 1–11 without notes or AI help.

- [ ] `study/00-how-to-use.md`: reading order, how to use the self-check questions, and the rule: answer aloud first, open `<details>` second
- [ ] `study/01-data-flow.md`: trace one `leg run` from `cli.py` to the exit code, citing file:line at each step; exercise: add a print at each step and run `leg run --fast`
- [ ] `study/02-eval-concepts.md`: faithfulness, answer relevancy, context recall, LLM-as-judge, and why each one misses failures the others catch
  - Use real cases from `sample_rag_qa.jsonl` as the examples
- [ ] `study/03-statistics.md`: pass/fail agreement, MAE, Pearson r, bootstrap CI, Cohen's kappa, and why n=17 gives a 47–88% interval
  - Exercise: recompute one CI by hand from `--json` output
- [ ] `study/04-decision-log.md`: one entry per non-obvious decision, each with the alternatives rejected and the evidence used
  - The 0.6/0.5 cutoffs
  - The lowered 70% bar
  - Deterministic checks gating CI, judge checks gating locally
  - Rule-based injection checks
  - Regex PII
  - The two judge roles
  - `context_recall` for the demo gate
- [ ] `study/05-code-walkthroughs.md`: line-by-line reading of the four trickiest pieces, with a "predict the output" exercise for each:
  - `security/injection.py` (refusal/quote window)
  - `core/calibration.py` (bootstrap)
  - `core/cache.py` (cache key)
  - `pytest_plugin.py` (auto-skip)
- [ ] `study/06-interview-drill.md`: 30+ likely interview questions with model answers
  - Covers design, statistics, security and the follow-up probes in Phases 13–17
- [ ] `study/07-ai-usage.md`: a skeleton only, with three sections: what I decided, what I rejected from the AI, what I verified by hand and how
  - Filling it in is a human step: it must be the maintainer's own account

**Definition of Done:** `study/00`–`07` exist; the maintainer has answered every self-check and drill question unaided at least once and has written `07-ai-usage.md` in their own words. **Not started.**

---

## Phase 13 — Labeling Rigor: Self-Agreement and a Second Labeler

Goal: know how consistent the ground truth is, which caps how good any judge can look.

- [x] Human step: do the pending Phase 7 self-agreement re-label (`scripts/relabel_sample.py sample|score`); record the number in `docs/datasets.md`
  - Done 2026-10-22: kappa 0.25 faithfulness / 0.00 relevancy (n=12); 5 differing cases, 3 against rules the guide already states
- [x] Add `docs/labeling-guide.md`: the scoring rubric for `human_faithfulness`/`human_relevancy` with one worked example per `failure_mode`
  - Why: a second labeler can't agree with rules that only exist in one person's head
  - Done: worked examples use an invented bike-share product, not dataset cases, so the guide doesn't leak labels to the second labeler
  - Per-case checklist added after self-agreement: 3 of 5 differing cases broke rules the guide already stated, 2 were false claims missed next to true ones
- [x] Extend `core/relabel.py` + `scripts/relabel_sample.py` with a `--labeler` field, plus Cohen's kappa and percent agreement between any two label sets; unit-test kappa against a hand-computed example
  - Done: `relabel_sample.py sample|score --labeler`, `compare A B`; `cohen_kappa` lives in `core/calibration.py`, so `calibrate_judge.py` reports the judge's kappa too; samples round up, so 20% is 12 cases, not 11
- [ ] Human step: a second person labels a random ≥20% sample using only the guide; report inter-rater kappa in `docs/datasets.md`; list disagreements and fix the guide (not the `test` labels)
  - `--exclude` the self-agreement sample: the checklist was revised on those 12 cases, so re-using them would inflate kappa
- [ ] Update `docs/judge-calibration.md`: compare judge agreement against the human ceiling
  - Judge side done: kappa reported (`test` faithfulness 0.43, relevancy 0.48); the human numbers fill in after the two human label passes
- [ ] `study/08-inter-rater-agreement.md`: why kappa rather than raw agreement, how to read 0.4 vs 0.8, and what to do when humans disagree

**Definition of Done:** self-agreement and inter-rater kappa are both documented; the labeling guide exists; kappa tooling is unit-tested. **In progress** — kappa tooling done and unit-tested; labeling guide written; self-agreement measured (kappa 0.25 / 0.00) and in the human-ceiling section; the second-labeler pass is open.

---

## Phase 14 — A Larger, Fresh Held-Out Set

Goal: a headline judge number with a confidence interval narrow enough to mean something.

- [ ] `study/09-sample-size.md`: how CI width shrinks with n; pick the target n for a ±10-point interval before collecting any data
- [ ] Add a `test2` split of ≥50 new cases to `sample_rag_qa.jsonl`, following the guide, with failure modes balanced as in Phase 7
  - Labels hand-written by the maintainer, not AI-drafted
  - Why: Phase 7's labels were AI-drafted then reviewed, and this split's job is to be independent evidence
- [ ] Extend `tests/unit/test_dataset.py` for `test2` (split name allowed, balance enforced)
- [ ] Run `scripts/calibrate_judge.py --split test2` once with the Phase 8 choice (`qwen2.5:7b`, 0.6/0.5); no tuning
- [ ] Update `docs/judge-calibration.md` with the result; if faithfulness reaches 80%, restore the bar (`MIN_PASS_RATE`); otherwise keep 70% and say why

**Definition of Done:** a ≥50-case `test2` split exists, is unit-tested, and has been run exactly once; the faithfulness bar decision is documented with the new interval. **Not started.**

---

## Phase 15 — Injection Detection Beyond Keywords

Goal: catch paraphrased compliance without losing a deterministic CI gate.

- [ ] Grow `datasets/redteam/` to ≥60 entries: a paraphrased variant of each existing attack, plus encoding tricks (base64, translated instructions, split payloads); synthetic data only
- [ ] Canary-token checks: indirect-injection payloads ask the model to emit a random token, and `ComplianceMetric` flags it exactly
  - Why: a token can't be paraphrased, so this stays deterministic
- [ ] Optional `JudgeComplianceMetric` (Ollama judge: "did the output carry out the injected instruction?") behind the existing `Metric` interface; local gating only, like the other judge metrics
- [ ] Calibrate it against hand labels on the demo app's red-team responses (the 68 verdicts from Phase 9); report agreement with a CI in `docs/security.md`
- [ ] Turn the paraphrase-FN strict `xfail` into a passing test under the judge metric (keep it `xfail` for the marker metric)
- [ ] `study/10-prompt-injection.md`: attack taxonomy, why marker matching fails, canary tokens, and the cost/variance trade-off of a judge

**Definition of Done:** ≥60 red-team entries; canary checks gate CI deterministically; the judge-compliance metric is calibrated and documented, with its limits stated. **Not started.**

---

## Phase 16 — An External System Under Test

Goal: show the gate finds real issues in a RAG app the maintainer didn't build.

- [ ] Pick an open-source RAG app that runs locally on Ollama at $0
  - Criteria: small, permissive license, an answer + retrieved-context API
  - Record the choice and the rejected candidates in `docs/test-strategy.md`
- [ ] Write a `generator:` adapter for it, out of tree or in `examples/external_rag/` with its own deps, so the package stays light
- [ ] Write a test plan for it before running anything: a short risk list adapted from `docs/test-strategy.md`
- [ ] Run the quality, red-team and `context_recall` suites; write `docs/external-case-study.md`: findings, false alarms, and what the gate couldn't check
- [ ] If findings are real and reproducible, file them upstream as issues (human step: outward-facing)
- [ ] `study/11-testing-unfamiliar-systems.md`: how to onboard a system you didn't write, from reading its code to a risk list to the first suite

**Definition of Done:** a case study with concrete findings (or a documented clean result with what was checked) against a third-party RAG app, and a reusable adapter. **Not started.**

---

## Phase 17 — Production-Scale Design (design doc, no new code)

Goal: a prepared, written answer to "how would this work on a real production system?"

- [ ] `docs/production-design.md`, one section each:
  - Large corpora: sampling cases, caching, and the cost of judge calls at 10k cases
  - Online monitoring vs pre-merge gating: sampling production traffic, detecting drift over time
  - Multi-turn conversations: how `EvalCase` would extend, and what metrics change
  - Ranking metrics (MRR, nDCG) once the generator no longer sees every chunk
  - Non-English input and bias: what labeled data would be needed
- [ ] For each section: what you'd build first, and what you'd measure to know it works
- [ ] `study/12-production-evals.md`: a self-check drill on the design doc

**Definition of Done:** the design doc exists, and the maintainer can whiteboard each section unaided. **Not started.**

---

## Phase 18 — Companion QA Portfolio (separate repo)

Goal: cover the conventional QA stack this repo deliberately leaves out. Planned and tracked in its own repo; listed here only so the portfolio story is complete.

- [ ] Create a separate repo with its own plan.md, covering:
  - UI E2E tests (Playwright)
  - API and contract tests
  - A performance smoke test
  - An exploratory test charter with bug reports
- [ ] Link it from this README's "Why" section once it has a passing CI run

**Definition of Done:** the companion repo exists with green CI and is linked from the README. **Not started.**

---

## Suggested Milestone Sequencing

- **M1 — Foundation** (Phases 0–1): repo scaffolded, lint/pre-commit enforced.
- **M2 — Quality Engine** (Phases 2–3): faithfulness/relevancy metrics and schema/prompt drift
  working locally.
- **M3 — Security Engine** (Phase 4): red-team suite operational.
- **M4 — Automation** (Phase 5): CI gate live, blocking merges.
- **M5 — Public Launch** (Phase 6): docs complete.
- **M6 — Credibility** (Phases 7–10): calibrated judge on a meaningful dataset, a real
  regression caught in a demo app, hardened security checks.
- **M7 — Release** (Phase 11): `v0.1.0` published to PyPI.
- **M8 — Ownership** (Phase 12): every decision defensible without notes or AI. Do this first:
  the later phases' study notes build on it.
- **M9 — Rigor** (Phases 13–15): measured human ceiling, a meaningful held-out number, injection
  checks that survive paraphrase.
- **M10 — Reach** (Phases 16–18): an external case study, a production design, the companion repo.

Treat M1–M2 as the critical path — nothing in Phases 4–6 is meaningfully testable without the `Metric`/`EvalCase` abstraction and the local runner from Phase 2–3 in place.
