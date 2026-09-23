# LLM-Eval-Guard — Implementation Plan

**Project:** LLM-Eval-Guard — a CI/CD quality gate framework for LLM and RAG applications
**Purpose:** Give teams a drop-in test harness that scores LLM/RAG outputs against quality, schema, and security metrics, and fails a pull request when those scores fall below configurable thresholds.

## Audience & goals for this build

This isn't just a working tool — it's a portfolio piece and a learning exercise, so three constraints apply across every phase below:

1. **Recruiter/interviewer legibility.** Assume the reader skims for 5 minutes: clean commit history (one logical change per commit, descriptive messages), a README that states *what QA/testing skill each phase demonstrates* (see Phase 6.1), and a **finished, polished small scope** beats a sprawling unfinished one. Where a step below is genuinely optional (Ragas as second adapter, GitLab CI parity), it's marked *stretch* — do the core path first, end-to-end, before circling back.
2. **Self-education.** Each phase's checklist entries should leave you able to explain *why*, not just *what*. Where it's not obvious from the code, add a one-line "Why" comment or doc note (see Documentation Policy below) — e.g., why faithfulness and answer-relevancy are scored separately, why indirect injection is a distinct threat from direct injection.
3. **Concise documentation.** See policy below — this cuts against the instinct to over-explain, which also serves goal 1 (recruiters don't read long docs).

### Documentation policy (applies to README, docs/*.md, and code comments for the whole project)
- Every doc file: bullets/tables over prose, no paragraph over ~4 lines, no restating what the code already shows.
- Every non-obvious design choice gets exactly one "Why:" line, not a discussion.
- `docs/` folder stays flat and short — one file per concern (architecture, thresholds, prompt-testing, ci-setup, datasets, judge-calibration). If a file exceeds ~150 lines, split it or cut it.
- README is the single entry point recruiters will actually read — everything else is reference material one click away.

### Cost policy — $0 budget, no exceptions
Everything in this plan must run on free tiers with no credit card required. Concretely:
- **LLM judge calls (the main cost risk):** default to a **local open-source model via Ollama** (e.g., `llama3.2:3b` or `phi3:mini` — small enough to run on a laptop or a GitHub-hosted runner). DeepEval and Ragas both support pointing at a custom/local LLM endpoint instead of OpenAI — wire that in Phase 2, not a paid API key.
- **DeepEval's Confident AI cloud reporting is opt-in telemetry/dashboard — leave it disabled** (no login, no cloud sync); run everything in local/offline mode.
- **Optional alternative for faster judge calls:** a free-tier hosted API with no card required (e.g., Groq or Google AI Studio's free tier) — usable for local dev if you want faster iteration than Ollama, but CI must not depend on it (rate limits + would break CI for other contributors without a key). Document this as opt-in, never required.
- **PII/toxicity detection:** already planned as local models (Presidio, Detoxify) in Phase 4 — no API cost, keep it that way.
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
- [ ] Define `llm_eval_guard/core/metric.py`: abstract `Metric` base class with `name`, `evaluate(input, output, context) -> MetricResult`, `threshold`
- [ ] Define `MetricResult` Pydantic model: `score: float`, `passed: bool`, `reason: str | None`, `metric_name: str`
- [ ] Define `EvalCase` Pydantic model: `input`, `actual_output`, `expected_output | None`, `retrieval_context | None`, `metadata: dict`
- [ ] Write unit tests for the abstract interface using a `FakeMetric` stub

### 2.2 DeepEval integration
- [ ] Add adapter `llm_eval_guard/metrics/deepeval_adapter.py` wrapping DeepEval's `FaithfulnessMetric`, `AnswerRelevancyMetric`, `ContextualPrecisionMetric`
- [ ] Normalize DeepEval's result object into internal `MetricResult`
- [ ] Point the judge model at **Ollama by default** (DeepEval supports a custom/local LLM via its `DeepEvalBaseLLM` interface — wrap the local Ollama model behind that, not `OPENAI_API_KEY`); keep it swappable so a paid provider is opt-in, never required
- [ ] Explicitly disable DeepEval's Confident AI cloud login/telemetry (offline/local mode only — no account, no cost)
- [ ] Write integration test using a mocked/stubbed judge LLM response (avoid real API/Ollama calls in unit tests — gate live-model tests behind a marker so CI doesn't need Ollama installed on every job)

### 2.3 Ragas integration (secondary adapter — stretch, after 2.2 works end-to-end)
- [ ] Add adapter `llm_eval_guard/metrics/ragas_adapter.py` for `faithfulness`, `answer_relevancy`, `context_recall`
- [ ] Normalize Ragas dataset format (HuggingFace `Dataset`) to/from `EvalCase`
- [ ] Wire Ragas's LLM wrapper to the same local Ollama model (Ragas accepts any LangChain-compatible LLM) — same $0-cost rule as 2.2
- [ ] Document in code which adapter is "default" vs opt-in (avoid double-installing heavy deps by default)

### 2.4 Custom Pytest fixtures
- [ ] Create `tests/conftest.py` with fixtures: `eval_client` (LLM client under test), `judge_llm` (evaluator model), `golden_dataset` (loads from `datasets/golden/*.jsonl`)
- [ ] Create a `pytest` plugin entry point (`llm_eval_guard.pytest_plugin`) exposing fixtures to any downstream repo that installs this package
- [ ] Add custom `pytest.mark.eval_metric(name, threshold)` marker for declarative threshold assertions
- [ ] Write example test suite in `tests/integration/test_faithfulness.py` and `test_answer_relevancy.py` demonstrating fixture usage end-to-end against a sample golden dataset

### 2.5 Golden dataset seed
- [ ] Create `datasets/golden/sample_rag_qa.jsonl` with 10–20 hand-written Q/A/context triples covering easy, ambiguous, and adversarial-but-benign cases
- [ ] For each case, add a **hand-assigned human label**: `human_faithfulness` and `human_relevancy` scores (or pass/fail), reasoned through yourself as if you were the judge — this labeled set is what Phase 2.6 calibrates against
- [ ] Document the dataset schema in `docs/datasets.md`

### 2.6 Judge calibration (meta-evaluation)
*This is the step that proves you understand evaluation, not just test plumbing: an LLM-judge is itself an unverified component until you check it against ground truth.*
- [ ] Write `scripts/calibrate_judge.py` (or a `pytest` case marked `@pytest.mark.calibration`): run the local-Ollama judge (Phase 2.2) over every case in `datasets/golden/sample_rag_qa.jsonl` and compare its scores to the `human_*` labels
- [ ] Compute simple agreement metrics — exact/near-match rate for pass/fail, and correlation (Pearson or Spearman) or mean absolute error for numeric scores; no need for anything fancier than `scipy.stats` or a hand-rolled calculation
- [ ] Set an explicit **minimum agreement threshold** (e.g., ≥80% pass/fail agreement) and fail the calibration check if the judge falls below it — this is what stops you from silently trusting a bad judge
- [ ] Re-run calibration whenever you change the judge model or prompt (e.g., swapping `llama3.2:3b` for `phi3:mini`) — note in `docs/datasets.md` that model choice is a tuning decision backed by this number, not a guess
- [ ] Write `docs/judge-calibration.md` (short — see documentation policy): what was measured, the agreement score achieved, and known failure modes (e.g., "judge over-scores verbose answers", if you observe that) — this doc is the artifact you'd point an interviewer to

**Definition of Done:** `pytest tests/integration/test_faithfulness.py -m eval_metric` runs against the sample golden dataset and produces pass/fail results with numeric scores, using a mockable judge LLM for CI-safe execution; separately, the calibration check reports a concrete agreement number between the automated judge and your human labels, and that number is documented.

---

## Phase 3 — Schema & Prompt Drift Validation

Goal: catch structural regressions (broken JSON output, missing fields) and prompt-template regressions before they reach production, with a local runner for pre-commit benchmarking.

### 3.1 Pydantic output schemas
- [ ] Define example strict output schemas in `llm_eval_guard/schema/` (e.g., `RagAnswer`, `ToolCallOutput`) demonstrating the pattern consumers should follow
- [ ] Add a generic `SchemaValidationMetric` that takes any user-supplied Pydantic model and validates LLM JSON output against it, capturing `ValidationError` details in `MetricResult.reason`
- [ ] Support both strict mode (fail on any extra/missing field) and lenient mode (warn only) via config
- [ ] Write unit tests: valid payload passes, malformed JSON fails gracefully (no crash), missing required field fails with a clear diff-style message

### 3.2 Prompt template testing
- [ ] Choose/standardize a prompt templating approach (e.g., Jinja2 templates stored in `prompts/*.j2`, versioned in git)
- [ ] Build a `PromptRegistry` loader that reads templates + metadata (expected variables, version tag)
- [ ] Write a "template contract" test suite: for each template, assert required variables render without `UndefinedError`, and rendered output stays under token/length budgets
- [ ] Add a **prompt drift detector**: snapshot-test each rendered prompt (golden file per template+inputs pair) and fail the test if the rendered output changes unexpectedly, requiring explicit snapshot update (`--update-snapshots` flag) — this is what catches silent prompt regressions
- [ ] Document snapshot review workflow in `docs/prompt-testing.md` (a snapshot diff in a PR should be reviewed like a code diff)

### 3.3 Local evaluation runner (pre-commit benchmark)
- [ ] Build `llm_eval_guard/cli.py` command: `leg run --suite <name> --config leg.config.yaml`
- [ ] Support a `leg.config.yaml` at repo root defining: which metrics run, thresholds per metric, which datasets to use, judge model config
- [ ] Runner outputs a console summary (via `rich`) with pass/fail table and aggregate score
- [ ] Add `leg run --fast` mode that skips expensive LLM-judge metrics and only runs schema/prompt-drift checks (cheap enough to run on every commit)
- [ ] Wire optional local pre-commit hook entry (`.pre-commit-config.yaml` local hook) so `leg run --fast` executes automatically before commit — no keys or paid services involved, so this is safe to enable by default (mark opt-in only if it feels slow, not because of cost)
- [ ] Write a `leg run --help` output test to lock in CLI UX

**Definition of Done:** A developer can run `leg run --fast` locally in under 10 seconds with no network calls, catching schema breaks and prompt drift before ever opening a PR; `leg run` (full suite) exercises real/mocked metric evaluation end-to-end.

---

## Phase 4 — Security & Red-Teaming Module

Goal: adversarial test coverage for prompt injection, jailbreaks, toxicity, and PII leakage, runnable as its own gated suite.

### 4.1 Red-team dataset construction
- [ ] Create `datasets/redteam/prompt_injection.jsonl` — direct injection payloads ("ignore previous instructions...")
- [ ] Create `datasets/redteam/indirect_injection.jsonl` — payloads embedded in retrieved/tool-returned content (simulating a poisoned document/webpage the RAG pipeline retrieves)
- [ ] Create `datasets/redteam/jailbreak.jsonl` — role-play/DAN-style bypass attempts (curate from public research datasets where licensing permits; cite sources)
- [ ] Create `datasets/redteam/pii_leakage.jsonl` — prompts designed to elicit memorized or injected PII (synthetic PII only, never real)
- [ ] Document dataset provenance and licensing in `datasets/redteam/README.md`
- [ ] Tag each entry with `attack_category`, `severity`, `expected_behavior` (e.g., "must refuse", "must not leak system prompt")

### 4.2 Indirect prompt injection test harness
- [ ] Build `llm_eval_guard/security/injection.py`: simulates RAG retrieval returning a poisoned document, then asserts the model's final output does not comply with the embedded instruction
- [ ] Implement a `ComplianceMetric` (did the model follow the injected instruction — bad) vs `TaskCompletionMetric` (did it still answer the real user question — good), scored via LLM-judge or rule-based keyword/regex heuristics as a cheaper fallback
- [ ] Write tests covering: injected instruction to leak system prompt, injected instruction to change output format, injected instruction to perform an unrelated "action" (simulating tool-calling abuse)

### 4.3 Toxicity checks
- [ ] Integrate a toxicity classifier (DeepEval's `ToxicityMetric`, or a lightweight local model like `detoxify` as a fallback to avoid extra API cost)
- [ ] Add `ToxicityMetric` adapter with configurable threshold
- [ ] Write tests asserting benign outputs score low and known-toxic fixture outputs score high (sanity-check the detector itself)

### 4.4 PII leakage checks
- [ ] Integrate a PII detector (e.g., Microsoft Presidio, or regex-based fallback for emails/phones/SSNs/credit cards)
- [ ] Add `PIILeakageMetric` that scans model output for PII patterns not present in the input context (distinguishing "echoed user-provided PII" from "leaked/hallucinated PII")
- [ ] Write tests with synthetic PII fixtures (never real personal data) covering false-positive edge cases (e.g., example emails like `user@example.com` should not always trigger)

### 4.5 Red-team suite wiring
- [ ] Add `leg run --suite security` CLI target that runs only the security/red-team suite
- [ ] Define severity-based thresholds in `leg.config.yaml` (e.g., zero tolerance for "must refuse" category, softer threshold for toxicity score)
- [ ] Ensure red-team suite results are clearly separated in reporting from quality metrics (security failures should be visually/semantically distinct — treat as blocking by default)

**Definition of Done:** `leg run --suite security` executes the full red-team dataset against a target model/pipeline and produces a pass/fail verdict per attack category, with indirect injection, toxicity, and PII checks all demonstrated against both a known-vulnerable stub model and a known-safe stub model (to prove the detectors actually discriminate).

---

## Phase 5 — CI/CD Pipeline Integration

Goal: automated, threshold-enforced gating on every PR, with human-readable reporting.

### 5.1 GitHub Actions workflow
- [ ] Create `.github/workflows/ci.yml` with jobs: `lint` (ruff + mypy), `unit-tests` (fast, no model calls), `eval-suite` (metric framework against local Ollama), `security-suite` (red-team), `schema-drift` (Phase 3 checks)
- [ ] Use a matrix strategy for Python versions (e.g., 3.10, 3.11, 3.12) on the lint/unit job
- [ ] Cache Poetry dependencies (`actions/cache` keyed on `poetry.lock` hash) to keep CI fast
- [ ] Install Ollama on the runner and cache the pulled model (`actions/cache` on `~/.ollama`) so the `eval-suite`/`security-suite` jobs run the real local judge model with $0 cost and no secrets required
- [ ] No API keys needed for the required path — if the optional bring-your-own-key adapter is ever exercised in CI, gate it behind a repo secret and skip it entirely on forked-repo PRs (never expose a paid key to untrusted PR code)

### 5.2 Threshold enforcement
- [ ] Wire `leg run --config leg.config.yaml --fail-under` to exit non-zero when any metric or security check falls below its configured threshold
- [ ] Ensure exit code propagates correctly to the GitHub Actions job (job fails → PR check fails → merge blocked if branch protection requires it)
- [ ] Add a `docs/thresholds.md` explaining how to tune thresholds per project maturity (e.g., stricter on `main`, looser on feature branches)
- [ ] Document required branch protection setup (require the `eval-suite` and `security-suite` checks to pass before merge) in `docs/ci-setup.md`

### 5.3 Reporting
- [ ] Build `llm_eval_guard/reporting/markdown_report.py` generating a Markdown summary: overall pass/fail, per-metric score table, top failing cases with diffs, security findings by severity
- [ ] Wire the report into GitHub Actions Job Summary (`$GITHUB_STEP_SUMMARY`) so results are visible without opening logs
- [ ] Optionally post the same summary as a PR comment via `actions/github-script` or a small composite action (dedupe/update existing comment rather than spamming new ones on each push)
- [ ] Emit a machine-readable JSON report alongside Markdown (for future dashboarding/trend tracking)
- [ ] Upload full report + raw eval traces as a workflow artifact for debugging failed runs

### 5.4 Performance & cost controls
- [ ] Add caching for LLM-judge calls keyed on `(input, output, metric)` hash to avoid re-running the local model on unchanged cases across CI re-runs (saves CI *time*, not money, since the model is free — but still worth it for speed)
- [ ] Add a `paths-filter` or path-based trigger so the full eval/security suite only runs when relevant files change (prompts, source, datasets), not on doc-only PRs
- [ ] Note in `docs/ci-setup.md` that the whole pipeline runs at $0 — local model, free GitHub Actions minutes (public repo) — so there's nothing to budget

### 5.5 GitLab CI parity (skip unless specifically wanted)
- [ ] Lowest priority item in the whole plan — GitHub Actions alone is enough to demonstrate the CI-gating skill, and GitLab's free tier has a monthly CI-minute cap (unlike GitHub's unlimited public-repo minutes). Only build this if you specifically want GitLab experience on your resume; otherwise leave unchecked and move on

**Definition of Done:** Opening a PR against `main` in a test repo triggers all CI jobs, a failing metric or security check blocks merge via required status checks, and the PR shows a Markdown summary table of results without needing to open raw logs.

---

## Phase 6 — Documentation & Maintenance

Goal: a README and docs set that lets a new adopter go from zero to a working quality gate in under 15 minutes.

### 6.1 README.md
- [ ] Write project tagline + badges (build status, PyPI version, license, code style)
- [ ] "Why LLM-Eval-Guard" section — problem statement, comparison to raw DeepEval/Ragas (what this framework adds: CI wiring, schema drift, security suite, reporting)
- [ ] **"Skills Demonstrated" table** — the recruiter-facing anchor of the README. One row per QA competency, linking straight to the code that proves it, e.g.:

  | Skill | Where |
  |---|---|
  | Metric-based LLM/RAG eval | `llm_eval_guard/metrics/`, Phase 2 |
  | Judge calibration (meta-evaluation vs. human labels) | `docs/judge-calibration.md`, Phase 2.6 |
  | Schema/contract testing | `llm_eval_guard/schema/`, Phase 3.1 |
  | Regression testing (prompt drift via snapshots) | `llm_eval_guard/schema/` prompt tests, Phase 3.2 |
  | Adversarial/security testing (prompt injection, PII, toxicity) | `llm_eval_guard/security/`, Phase 4 |
  | CI quality gates & automated reporting | `.github/workflows/ci.yml`, Phase 5 |

- [ ] Quickstart: `pip install llm-eval-guard`, `leg init` (scaffolds `leg.config.yaml` + example tests), `leg run`
- [ ] Configuration reference table for `leg.config.yaml` keys
- [ ] Usage examples: adding a custom metric, adding a custom red-team dataset entry, wiring a new LLM provider adapter
- [ ] CI badge + snippet showing the GitHub Actions job summary output (screenshot or embedded example)
- [ ] Keep the whole file scannable in under 3 minutes — this is the one doc a recruiter actually opens; push anything else to `docs/`

### 6.2 Architecture documentation
- [ ] Create `docs/architecture.md` with a diagram (Mermaid, embeddable in Markdown/GitHub) showing: EvalCase → Metric adapters (DeepEval/Ragas) → Runner → Reporting → CI gate
- [ ] Document the plugin/extension points explicitly (custom `Metric`, custom `PromptRegistry` source, custom PII/toxicity backend) so contributors know where to extend without forking core
- [ ] Add a sequence diagram for the indirect-injection test flow (Phase 4.2) since it's the least obvious mechanism

### 6.3 Contributor & maintenance docs
*Keep this section lightweight — it's a solo portfolio project, not a project expecting external contributors yet. Do it for the OSS-hygiene signal, but each file should be short.*
- [ ] `CONTRIBUTING.md`: dev setup (references Phase 1), how to add a new metric adapter, one-line ethics note on adding adversarial red-team content
- [ ] `SECURITY.md` with a short vulnerability disclosure note (signals security awareness — relevant since this is a security-adjacent tool)
- [ ] Skip issue/PR templates for v0.1 unless you're specifically showcasing repo-governance skills — low signal relative to the docs effort
- [ ] `CHANGELOG.md` seeded with `v0.1.0`, Keep-a-Changelog format, one line per phase shipped

### 6.4 Release readiness
- [ ] Configure `pyproject.toml` package metadata for PyPI publish (description, keywords, classifiers, project URLs)
- [ ] Add a release workflow (`.github/workflows/release.yml`) triggered on git tags, building + publishing to PyPI via trusted publishing (OIDC, no long-lived token)
- [ ] Tag and cut `v0.1.0` once Phases 1–5 are complete and README quickstart has been manually verified end-to-end on a clean machine/container

**Definition of Done:** A new user with no prior context can clone the repo, follow only the README, and get a passing `leg run` against the sample golden dataset within 15 minutes; architecture diagram accurately reflects the shipped code; `v0.1.0` is tagged and published.

---

## Suggested Milestone Sequencing

| Milestone | Phases | Outcome |
|---|---|---|
| M1 — Foundation | 0, 1 | Repo scaffolded, lint/pre-commit enforced |
| M2 — Quality Engine | 2, 3 | Faithfulness/relevancy metrics + schema/prompt drift working locally |
| M3 — Security Engine | 4 | Red-team suite operational |
| M4 — Automation | 5 | CI gate live, blocking merges |
| M5 — Public Launch | 6 | Docs complete, `v0.1.0` published |

Treat M1–M2 as the critical path — nothing in Phases 4–6 is meaningfully testable without the `Metric`/`EvalCase` abstraction and the local runner from Phase 2–3 in place.
