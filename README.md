# LLM-Eval-Guard

<!-- Why absolute links: this README is also the PyPI page, where relative links break. -->
[![CI](https://github.com/PimySoft/llm-eval-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/PimySoft/llm-eval-guard/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/llm-eval-guard.svg)](https://pypi.org/project/llm-eval-guard/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/PimySoft/llm-eval-guard/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> A CI/CD quality gate for LLM and RAG applications — scores outputs against quality, schema,
> and security metrics, and fails a pull request when thresholds aren't met.

Status: feature-complete for `v0.1.0` (pre-release). Charter: [VISION.md](https://github.com/PimySoft/llm-eval-guard/blob/main/VISION.md) · roadmap:
[plan.md](https://github.com/PimySoft/llm-eval-guard/blob/main/plan.md).

## Why

A bad prompt edit, a broken retrieval step or a regressed output schema merges silently, because
nothing fails CI. LLM-Eval-Guard is that missing gate: `pytest --cov` discipline for model outputs.

It's a gating and reporting layer on top of [DeepEval](https://github.com/confident-ai/deepeval),
not a replacement. What it adds:

- **One `Metric` interface** over engine scores — [`metrics/`](https://github.com/PimySoft/llm-eval-guard/tree/main/llm_eval_guard/metrics)
- **$0 local judge by default** (Ollama); OpenAI/Anthropic only as bring-your-own-key
- **Judge calibration** against human labels — [docs/judge-calibration.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/judge-calibration.md)
- **Schema/contract testing**, strict or lenient — [`schema/`](https://github.com/PimySoft/llm-eval-guard/tree/main/llm_eval_guard/schema)
- **Prompt-drift snapshots** for Jinja2 templates — [`prompts/`](https://github.com/PimySoft/llm-eval-guard/tree/main/llm_eval_guard/prompts)
- **Red-team suite**: prompt injection, jailbreak, PII, toxicity — [`security/`](https://github.com/PimySoft/llm-eval-guard/tree/main/llm_eval_guard/security)
- **CI gating + reporting**: `leg run` exit code, job-summary report — [`ci.yml`](https://github.com/PimySoft/llm-eval-guard/blob/main/.github/workflows/ci.yml)
- **Test strategy**: risk → check, and what's left out on purpose — [docs/test-strategy.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/test-strategy.md)

## Quickstart

```bash
pip install "llm-eval-guard[deepeval]"
ollama pull qwen2.5:7b          # local, $0-cost calibrated judge

leg init                        # scaffolds leg.config.yaml + a sample dataset + example test
leg run                         # full suite, scored by the local Ollama judge
leg run --fast                  # schema/prompt-drift/rule checks only, no network call
```

From Python, or inside a pytest test via the `judge_llm` fixture:

```python
from llm_eval_guard.core import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import faithfulness_metric

case = EvalCase(
    input="What's the storage limit on the Free plan?",
    actual_output="The Free plan includes 5GB of storage.",
    retrieval_context=["Free plan limits: 5GB total storage, 2GB max file size per upload."],
)
result = faithfulness_metric(threshold=0.8).evaluate(case)  # pass model=judge_llm in pytest
print(result.score, result.passed, result.reason)
```

Full pytest pattern: `tests/integration/test_faithfulness.py`. A paid judge is opt-in: pass any
DeepEval model, e.g. `model=OpenAIModel(model="gpt-4o-mini")`.

## Configuration

`leg.config.yaml` at the project root drives every `leg run`:

```yaml
suites:
  quality:
    dataset: datasets/golden/sample_rag_qa.jsonl
    metrics:
      - name: faithfulness
        threshold: 0.6        # calibrated judge cutoff
judge:
  model: qwen2.5:7b           # calibrated judge
judge_profiles:
  ci:
    model: qwen2.5:0.5b       # fast, uncalibrated: `leg run --judge ci`
```

- Every key: [docs/architecture.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/architecture.md#legconfigyaml-reference)
- Why these thresholds: [docs/thresholds.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/thresholds.md)
- Custom metric, schema or prompt source: [docs/architecture.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/architecture.md#extension-points)
- New red-team entry: [`datasets/redteam/README.md`](https://github.com/PimySoft/llm-eval-guard/blob/main/datasets/redteam/README.md)

## What a CI run looks like

`leg run --report-dir reports/` writes `report.md` into the GitHub Actions job summary:

```markdown
# LLM-Eval-Guard Report

**✅ PASS** — 12/12 cases passed (100%)

## Per-metric summary

- **quality / faithfulness** — 6/6 passed (100%), avg score 0.95
- **security / compliance** — 6/6 passed (100%), avg score 1.00
```

Security failures get their own section, sorted by severity — see [docs/security.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/security.md#reporting).

## A caught regression

The gate also runs against a real (tiny) RAG app, [`examples/demo_rag`](https://github.com/PimySoft/llm-eval-guard/tree/main/examples/demo_rag).
[PR #2](https://github.com/PimySoft/llm-eval-guard/pull/2) changes `TOP_K = 3` → `1` ("one chunk
is enough") and CI goes red ([run](https://github.com/PimySoft/llm-eval-guard/actions/runs/39652782076)).

![demo-rag job summary on the regression PR: context_recall 8/12, four multi-hop questions missing a fact](https://raw.githubusercontent.com/PimySoft/llm-eval-guard/main/docs/img/regression-demo-summary.png)

- **CI gate (`context_recall`):** 12/12 → 8/12, exit 1 — every multi-hop question loses a fact.
  Deterministic, so no judge noise.
- **Calibrated judge:** 20/24 → 19/24. "The context doesn't say" is *faithful*, so judge
  metrics barely move — why the gate checks retrieval directly.
- PR #2 stays open, never merged, as evidence. Red-team results for the same app:
  [docs/security.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/security.md#against-a-real-app-the-demo-rag-bot).

## Development

```bash
make install && poetry run pre-commit install && make test
```

- Prerequisites and workflow: [CONTRIBUTING.md](https://github.com/PimySoft/llm-eval-guard/blob/main/CONTRIBUTING.md)
- Judge trust: the default judge agrees with human labels 82% (relevancy) and 71% (faithfulness)
  held-out — read [docs/judge-calibration.md](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/judge-calibration.md) before trusting scores

## Docs

- [architecture](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/architecture.md) — data flow, config keys, extension points
- [thresholds](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/thresholds.md) — every cutoff and why
- [datasets](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/datasets.md) — golden dataset schema and labeling rules
- [prompt-testing](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/prompt-testing.md) — prompt contracts and drift snapshots
- [security](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/security.md) — red-team metrics and findings
- [ci-setup](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/ci-setup.md) — CI jobs, branch protection, release
- [judge-calibration](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/judge-calibration.md) — how far to trust the judge
- [test-strategy](https://github.com/PimySoft/llm-eval-guard/blob/main/docs/test-strategy.md) — risks, checks, and gaps
