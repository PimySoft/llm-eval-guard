# Changelog

All notable changes to this project are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Phase 13:** `scripts/relabel_sample.py` takes `--labeler` and a `compare A B` command, and
  reports Cohen's kappa and the differing case ids alongside agreement; `calibrate_judge.py`
  reports the judge's kappa too. Blind samples now round up (20% of 56 is 12 cases, not 11).
- [docs/labeling-guide.md](docs/labeling-guide.md): the faithfulness/relevancy rubric with one
  worked example per failure mode, written so a second labeler can work from it alone.
- `docs/judge-calibration.md` reports judge kappa (`test`: faithfulness 0.43, relevancy 0.48) and
  a human-ceiling section that the human label-agreement numbers fill in.
- Labeler self-agreement measured on a blind 12-case re-label: kappa 0.25 faithfulness, 0.00
  relevancy ([docs/datasets.md](docs/datasets.md#label-agreement)); the filled-in
  `sample_rag_qa.relabel.jsonl` is committed as evidence.

### Fixed

- README links and the regression screenshot are absolute GitHub URLs, so they work on the
  PyPI project page too (relative ones broke there in 0.1.0).

## [0.1.0] — 2026-10-22

### Added

- **Phase 0–1:** Project charter (`VISION.md`), Apache-2.0 license, Poetry workspace, Ruff/mypy/
  pre-commit tooling.
- **Phase 2:** `Metric`/`EvalCase`/`MetricResult` abstraction; DeepEval adapter (faithfulness,
  answer relevancy, contextual precision) scored by a local Ollama judge; pytest fixtures
  (`eval_client`, `judge_llm`, `golden_dataset`) and the `eval_metric`/`calibration` markers;
  golden RAG QA dataset with hand-labeled ground truth; judge-calibration harness
  (`scripts/calibrate_judge.py`, [docs/judge-calibration.md](docs/judge-calibration.md)).
- **Phase 3:** Pydantic output-schema validation (`SchemaValidationMetric`, strict/lenient modes);
  Jinja2 `PromptRegistry` with contract tests and prompt-drift snapshot testing
  ([docs/prompt-testing.md](docs/prompt-testing.md)); `leg run`/`leg run --fast` CLI.
- **Phase 4:** Red-team datasets (direct/indirect prompt injection, jailbreak, PII elicitation);
  `ComplianceMetric`/`TaskCompletionMetric` for injection defense; toxicity via the DeepEval/
  Ollama judge; regex-based `PIILeakageMetric`; `leg run --suite security`
  ([docs/security.md](docs/security.md)).
- **Phase 5:** GitHub Actions CI (`lint`, `unit-tests`, `schema-drift`, `eval-suite`,
  `security-suite`) with path-based triggering and Ollama caching; judge-result caching
  (`core/cache.py`); Markdown/JSON reporting into `$GITHUB_STEP_SUMMARY` and workflow artifacts
  ([docs/ci-setup.md](docs/ci-setup.md), [docs/thresholds.md](docs/thresholds.md)).
- **Phase 6:** `leg init` scaffolding command; README skills-demonstrated table and quickstart;
  [docs/architecture.md](docs/architecture.md) with data-flow and indirect-injection sequence
  diagrams; `SECURITY.md`; PyPI package metadata and a tag-triggered release workflow.
- **Phase 7:** golden dataset grown to 56 cases (28 pass / 28 fail), each tagged with a
  `failure_mode` and a `dev`/`test` split (39/17), enforced by `tests/unit/test_dataset.py`;
  `scripts/relabel_sample.py` samples and scores a blind human re-label pass
  ([docs/datasets.md](docs/datasets.md)).
- **Phase 8:** `scripts/calibrate_judge.py --split dev|test` reports per-`failure_mode`
  agreement, seconds per case, and a bootstrap 95% confidence interval, plus per-metric judge
  cutoffs and per-case scores in `--json`. Six local judges compared on `dev`; the default judge
  is now the calibrated `qwen2.5:7b` ([docs/judge-calibration.md](docs/judge-calibration.md)).
  `judge_profiles` in `leg.config.yaml` plus `leg run --judge <name>` / `LEG_JUDGE_PROFILE`
  select the fast, uncalibrated `ci` judge (`qwen2.5:0.5b`) that CI runs. Quality-suite
  thresholds set to the calibrated cutoffs (faithfulness 0.6, answer_relevancy 0.5).
  Judge-scored integration tests are strict `xfail`s only under the `ci` judge.
- **Phase 9:** demo RAG app in `examples/demo_rag/` — markdown knowledge base,
  hand-rolled BM25 retriever, generation through `prompts/rag_answer.j2` on local Ollama;
  `GenerationCache` in `core/cache.py` caches its answers keyed on model + rendered prompt.
  Suites accept a `generator: module.path:function` that produces each case's output from the
  system under test at run time (skipped under `--fast`); new rule-based `context_recall` metric;
  `demo`/`demo_quality` suites and a `demo-rag` CI job gated on `leg run --suite demo`.
  `demo_security` suite runs the red-team datasets against the demo app; findings in
  [docs/security.md](docs/security.md). Red-team failures now render as security findings in any
  suite (keyed on `attack_category`, not the suite name `security`).
  [docs/test-strategy.md](docs/test-strategy.md): risk → check map and deliberate non-coverage.
  README "A caught regression": top-1 retrieval regression caught by the `demo` gate (12/12 →
  8/12) while the calibrated judge barely moved (20/24 → 19/24); the red regression PR (#2) and
  its job-summary screenshot are linked from the README.
- **Phase 10:** `PIILeakageMetric` detects UK National Insurance numbers, UK
  phone numbers, UK postcodes and IBANs; credit cards must pass a Luhn check and IBANs mod-97, so
  arbitrary 16-digit IDs no longer fail; echoed PII matches regardless of spacing/hyphens.
  `ComplianceMetric` ignores markers inside quoted spans or after a same-clause refusal ("I won't
  wire $500"); remaining marker-matching limits documented in
  [docs/security.md](docs/security.md#remaining-limits-of-marker-matching).
  Test suite runs warning-free: `xfail_strict = true`, `asyncio_default_fixture_loop_scope` set,
  and a `DeprecationWarning` from `llm_eval_guard` code is now a test error. Coverage is measured
  with `coverage run -m pytest` (pytest-cov started after our `pytest11` entry point imported the
  package, under-reporting 96% as 67%); the `unit-tests` CI job and `make cov` fail below 80%.

### Fixed

- `import llm_eval_guard.security` (or `.schema`/`.metrics`) as a program's first import no longer
  fails with a circular `ImportError`; `core`'s runner re-exports are now lazy. Caught by a new
  per-module cold-import test.
- A judge-metric call that raises (e.g. the 0.5B `ci` judge looping until DeepEval's timeout) now
  fails that one case with a `judge error` reason instead of crashing the whole `leg run`; errored
  results aren't cached. Rule-based metric errors still raise.
- Demo app caps answers at 512 tokens — greedy decoding on `qwen2.5:0.5b` looped until the 300 s
  timeout in CI.
- CLI `--help` tests failed on GitHub Actions, where Typer forces Rich colour codes into the help
  text; ANSI escapes are now stripped before asserting.
- Judge-result cache (`core/cache.py`) now keys on the judge model and threshold too — switching
  either previously served stale scores and pass/fail calls from the old one.
- `leg init`'s scaffolded suite now includes a rule-based `pii_leakage` check, so the
  quickstart's `leg run --fast` scores the sample case instead of evaluating nothing; found
  verifying the quickstart from a built wheel in a clean container.
- `leg --help` no longer prints an internal developer note as the CLI description.
- README quickstart quotes `"llm-eval-guard[deepeval]"` — unquoted, zsh treats the brackets as
  a glob and the install fails.
- `docs/ci-setup.md` release setup now uses a PyPI *pending* trusted publisher; it described
  registering the project first, which PyPI doesn't allow before a first upload.

### Changed

- `report.md` sections (per-metric summary, security findings, failing cases) are bullet lists
  instead of Markdown tables, so the report reads top to bottom in the job summary and raw file.
- Documentation condensed: each fact lives in one doc and the others link to
  it; README's DeepEval comparison and skills list merged into one "Why" list;
  `docs/architecture.md` prose replaced by numbered step lists, keeping the data-flow and
  indirect-injection diagrams Phase 6.2 requires; `docs/security.md`'s demo-bot
  findings and marker limits no longer repeat each other; `docs/judge-calibration.md` opens
  with a three-line summary.

### Known limitations

- The human self-agreement number for the golden labels (Phase 7) is pending a blind re-label
  pass, so the ceiling on judge agreement isn't measured yet.

- Held-out faithfulness agreement for the default judge is 71%, below the 80% bar; it's gated at
  a documented, lowered 70% bar — see [docs/judge-calibration.md](docs/judge-calibration.md).
- CI runs the uncalibrated `ci` judge; the calibrated `qwen2.5:7b` is too slow for a free CPU
  runner, so calibrated gating is local/self-hosted only ([docs/ci-setup.md](docs/ci-setup.md)).
- Ragas (second metric-engine adapter) and GitLab CI parity are stretch goals, deferred per
  `plan.md`'s Phase 2.3/5.5 scope notes.
