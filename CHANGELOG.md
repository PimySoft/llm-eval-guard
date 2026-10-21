# Changelog

All notable changes to this project are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] — Unreleased

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
- **Phase 8 (in progress):** `scripts/calibrate_judge.py --split dev|test` reports per-
  `failure_mode` agreement, wall-clock seconds per case, and a bootstrap 95% confidence interval
  on agreement, plus per-metric judge cutoffs (`--faithfulness-threshold`, `--relevancy-threshold`)
  and per-case scores in `--json`. Six local judges compared on the `dev` split
  ([docs/judge-calibration.md](docs/judge-calibration.md)).
- **Phase 8:** default judge is now the calibrated `qwen2.5:7b`; `judge_profiles` in
  `leg.config.yaml` plus `leg run --judge <name>` / `LEG_JUDGE_PROFILE` select the fast,
  uncalibrated `ci` judge (`qwen2.5:0.5b`) that CI runs. Quality-suite thresholds set to the
  calibrated judge cutoffs (faithfulness 0.6, answer_relevancy 0.5). Judge-scored integration
  tests are strict `xfail`s only under the `ci` judge.
- **Phase 9 (in progress):** demo RAG app in `examples/demo_rag/` — markdown knowledge base,
  hand-rolled BM25 retriever, generation through `prompts/rag_answer.j2` on local Ollama;
  `GenerationCache` in `core/cache.py` caches its answers keyed on model + rendered prompt.
  Suites accept a `generator: module.path:function` that produces each case's output from the
  system under test at run time (skipped under `--fast`); new rule-based `context_recall` metric;
  `demo`/`demo_quality` suites and a `demo-rag` CI job gated on `leg run --suite demo`.
  `demo_security` suite runs the red-team datasets against the demo app; findings in
  [docs/security.md](docs/security.md). Red-team failures now render as security findings in any
  suite (keyed on `attack_category`, not the suite name `security`).
  [docs/test-strategy.md](docs/test-strategy.md): risk → check map and deliberate non-coverage.

### Fixed

- Judge-result cache (`core/cache.py`) now keys on the judge model and threshold too — switching
  either previously served stale scores and pass/fail calls from the old one.

### Known limitations

- Held-out faithfulness agreement for the default judge is 71%, below the 80% bar; it's gated at
  a documented, lowered 70% bar — see [docs/judge-calibration.md](docs/judge-calibration.md).
- CI runs the uncalibrated `ci` judge; the calibrated `qwen2.5:7b` is too slow for a free CPU
  runner, so calibrated gating is local/self-hosted only ([docs/ci-setup.md](docs/ci-setup.md)).
- Ragas (second metric-engine adapter) and GitLab CI parity are stretch goals, deferred per
  `plan.md`'s Phase 2.3/5.5 scope notes.
