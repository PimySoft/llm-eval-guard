# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LLM-Eval-Guard (`llm_eval_guard`, CLI: `leg`) is a pytest-native CI/CD quality gate for LLM/RAG
apps: scores outputs against quality, schema, and security metrics and fails the build below
threshold. Problem statement, target user, and non-goals are in [VISION.md](VISION.md); the
phased build roadmap with per-phase Definition of Done is in [plan.md](plan.md) — check plan.md
before assuming a module described below actually exists yet.

**Current state:** Phases 1–11 done; `v0.1.0` is on PyPI. Open: Phase 7's human
self-agreement re-label pass, and Phases 12–18 (portfolio hardening; study guides go in `study/`).
plan.md checkboxes are the source of truth. When building a phase, follow its plan.md checklist
rather than improvising a different shape.

## Workflow

- One logical change per commit, per plan.md sub-section. In the same commit, tick the plan.md
  checkbox, update that phase's Definition of Done note, and add a `CHANGELOG.md` entry under
  the unreleased version.
- Human-only steps — never do these unprompted: `git push`, `git tag`/`git push --tags`, making
  the repo public, PyPI trusted-publisher setup, and the Phase 7 self-agreement re-label.

## Commands

```bash
poetry install --extras deepeval   # deps (equivalent to `make install`)
poetry run pre-commit install      # git hooks (required once per clone)

make lint       # ruff check .
make format     # ruff format .
make typecheck  # mypy
make test       # pytest
make cov        # coverage run -m pytest + report; fails under 80% (same gate as CI)

poetry run python scripts/calibrate_judge.py --model <ollama-model>   # judge vs human labels
```

Single test: `poetry run pytest tests/unit/test_package.py::test_package_is_importable` or
`poetry run pytest -k <expr>`.

Live-judge (`live_llm`-marked) tests need [Ollama](https://ollama.com) running locally with
`ollama pull qwen2.5:7b` pulled (auto-skip otherwise, see `llm_eval_guard/pytest_plugin.py`);
plain unit tests don't require it (see Cost policy). Two judge roles: `qwen2.5:7b` is the
calibrated default; `qwen2.5:0.5b` is the uncalibrated `ci` profile, under which judge-scored
integration tests are strict xfails (`tests/integration/_judge.py`). See `docs/judge-calibration.md`.

## Coding standards

- Ruff (`pyproject.toml` `[tool.ruff]`): line length 100, rule sets `E, F, I, UP, B, SIM`, double
  quotes. `make format` before committing; pre-commit runs `ruff --fix` + `ruff-format` anyway.
- mypy strict on `llm_eval_guard/`; relaxed (`disallow_untyped_defs = false`) on `tests/`.
- `.pre-commit-config.yaml` also runs trailing-whitespace/EOF-fixer/check-yaml/large-file/private-key
  checks — don't bypass with `--no-verify`.
- Documentation policy (README, `docs/*.md`, code comments) per plan.md: bullet lists over
  prose, no Markdown tables, no paragraph over ~4 lines, one "Why:" line for a non-obvious design
  choice rather than a discussion, don't restate what the code already shows. `docs/` stays flat,
  one file per concern, split a file past ~150 lines.
- `xfail` must be `strict=True` with a `reason`; never add a non-strict one (`xfail_strict = true`
  in `pyproject.toml` makes strict the default). Judge-dependent
  ones use `xfail_under_ci_judge` (`tests/integration/_judge.py`).
- `examples/` (Phase 9 demo app): ruff already covers it; add it to mypy `files` in
  `pyproject.toml` when created. No new heavy dependency (hand-rolled keyword/BM25 retriever);
  cache generated outputs via `core/cache.py`. The regression-demo branch/PR is never merged.

## Architecture (Phase 2+ design — see plan.md for exact phase gating)

Everything normalizes through one abstraction so metric/schema/security checks and reporting all
compose the same way:

- `EvalCase` (pydantic): `input`, `actual_output`, `expected_output | None`, `retrieval_context | None`, `metadata`
- `Metric` (ABC): `name`, `evaluate(input, output, context) -> MetricResult`, `threshold`
- `MetricResult` (pydantic): `score`, `passed`, `reason`, `metric_name`

Data flow: `EvalCase` → `Metric` adapter (DeepEval today; Ragas is a stretch second adapter behind
the same interface, added only after DeepEval is complete end-to-end) → `MetricResult` →
`reporting/` (Markdown + JSON) → CLI exit code gates CI.

Package layout (`llm_eval_guard/`):
- `core/` — `Metric`/`EvalCase` interfaces, `leg.config.yaml` loader (`config.py`), metric-name
  registry (`registry.py`), suite runner (`runner.py`)
- `metrics/` — engine adapters (`deepeval_adapter.py` first); normalizes engine-native results into `MetricResult`
- `schema/` — pydantic output-contract validators (`SchemaValidationMetric`, strict vs lenient mode)
- `prompts/` — Jinja2 `PromptRegistry` (`prompts/*.j2` + `.meta.yaml` sidecars) and prompt-drift
  snapshot testing (`assert_matches_snapshot`) — a plain pytest mechanism, not a `Metric`, see
  `docs/prompt-testing.md`
- `security/` — red-team harness: `ComplianceMetric`/`TaskCompletionMetric` (`injection.py`, rule-based
  keyword checks for direct/indirect prompt injection and jailbreaks) and `PIILeakageMetric`
  (`pii.py`, regex-based). Toxicity is a DeepEval-adapter metric (`metrics/deepeval_adapter.py`),
  not a `security/` module — see `docs/security.md`
- `reporting/` — Markdown/JSON report generators, wired into `$GITHUB_STEP_SUMMARY`
- `cli.py` — `leg` CLI (`leg run --suite <name> --config leg.config.yaml`, `leg init`); `leg run --fast` skips LLM-judge metrics for a pre-commit-speed schema/drift-only pass.

A `pytest` plugin entry point (`llm_eval_guard.pytest_plugin`) exposes fixtures (`eval_client`,
`judge_llm`, `golden_dataset`) to *downstream* repos that install this package — this is a second,
public consumption surface, not just internal test infra. Custom markers: `eval_metric(name,
threshold)`, `calibration` (`pyproject.toml` `[tool.pytest.ini_options]`).

## Cost policy — $0, no exceptions

- Ollama (local) is the **default and required** judge path; OpenAI/Anthropic adapters are
  documented bring-your-own-key opt-ins, never required to get a passing build.
- DeepEval's Confident AI cloud telemetry/login must stay disabled (local/offline mode only).
- Toxicity uses the local Ollama judge (DeepEval's `ToxicityMetric`); PII detection is regex-based
  (`security/pii.py`) — no paid APIs, no extra heavy ML dependency.
- Gate any test that calls a real judge LLM behind a marker so the default `pytest`/unit run needs
  no network call and no Ollama install; mock/stub the judge response in unit tests instead.

## Datasets

- `datasets/golden/*.jsonl` — hand-written RAG QA/context triples, each with hand-assigned
  `human_faithfulness`/`human_relevancy` labels used to calibrate the LLM judge against ground
  truth (Phase 2.6 — the judge is only trusted once it's checked against these).
  `sample_rag_qa.jsonl` cases also carry `id`, `split` (`dev`/`test`), `category` and
  `failure_mode` — rules in `docs/datasets.md`, enforced by `tests/unit/test_dataset.py`.
- Split discipline: select/tune judge models on `split: dev` only; report `test` numbers once, for
  the final model. Never edit a `test` case's labels after seeing judge scores.
- Changing the judge (`judge.model` in `leg.config.yaml` or the default in
  `metrics/deepeval_adapter.py`) requires re-running `scripts/calibrate_judge.py` and updating
  `docs/judge-calibration.md` in the same commit.
- `datasets/redteam/*.jsonl` — adversarial payloads (prompt injection, jailbreak, PII-elicitation).
  Every entry must carry `attack_category`, `severity`, `expected_behavior`, and must never contain
  real PII — synthetic data only (see CONTRIBUTING.md).
