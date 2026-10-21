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

### Known limitations

- The shipped default judge (`qwen2.5:0.5b`) fails its own calibration bar — see
  [docs/judge-calibration.md](docs/judge-calibration.md). Judge-scored tests are marked
  `xfail(strict=False)` until a better-calibrated model is swapped in.
- Ragas (second metric-engine adapter) and GitLab CI parity are stretch goals, deferred per
  `plan.md`'s Phase 2.3/5.5 scope notes.
