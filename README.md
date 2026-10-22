# LLM-Eval-Guard

[![CI](https://github.com/PimySoft/llm-eval-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/PimySoft/llm-eval-guard/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/llm-eval-guard.svg)](https://pypi.org/project/llm-eval-guard/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> A CI/CD quality gate for LLM and RAG applications — scores outputs against quality, schema,
> and security metrics, and fails a pull request when thresholds aren't met.

Status: feature-complete for `v0.1.0` (pre-release). Charter: [VISION.md](VISION.md) · roadmap:
[plan.md](plan.md).

## Why LLM-Eval-Guard

Teams shipping an LLM/RAG feature have no equivalent of a unit-test gate: a bad prompt edit, a
broken retrieval step, or a regressed output schema merges silently because nothing fails CI.
LLM-Eval-Guard is that gate — the same discipline `pytest --cov` gives regular code, applied to
model outputs.

It's not a replacement for [DeepEval](https://github.com/confident-ai/deepeval) or
[Ragas](https://github.com/explodinggradients/ragas) — it's a CI-gating and reporting layer built
on top of one (DeepEval today). What it adds on top of the raw eval engine:

- **Metric scoring** — raw DeepEval/Ragas already do this; LLM-Eval-Guard wraps it behind one
  `Metric` interface.
- **$0-cost local judge by default** — raw engines leave this opt-in, wired up yourself;
  LLM-Eval-Guard requires the Ollama path, with OpenAI/Anthropic documented as bring-your-own-key.
- **Schema/contract testing** — not in raw DeepEval/Ragas; LLM-Eval-Guard adds
  `SchemaValidationMetric` (strict/lenient).
- **Prompt-drift regression testing** — not in raw DeepEval/Ragas; LLM-Eval-Guard adds Jinja2
  snapshot testing.
- **Adversarial/red-team suite** — not in raw DeepEval/Ragas; LLM-Eval-Guard adds prompt
  injection, jailbreak, PII, and toxicity checks.
- **Judge calibration against human labels** — not in raw DeepEval/Ragas; LLM-Eval-Guard adds
  `scripts/calibrate_judge.py`.
- **CI wiring + threshold gating** — you build it yourself on raw engines; LLM-Eval-Guard ships
  `leg run`, GitHub Actions wiring, and exit-code gating.
- **Human-readable CI reporting** — you build it yourself on raw engines; LLM-Eval-Guard writes
  Markdown into `$GITHUB_STEP_SUMMARY` plus a JSON artifact.

## Skills demonstrated

- **Metric-based LLM/RAG evaluation** — [`llm_eval_guard/metrics/`](llm_eval_guard/metrics/)
- **Judge calibration** (meta-evaluation vs. human labels) — [docs/judge-calibration.md](docs/judge-calibration.md)
- **Schema/contract testing** — [`llm_eval_guard/schema/`](llm_eval_guard/schema/)
- **Regression testing** (prompt drift via snapshots) — [`llm_eval_guard/prompts/`](llm_eval_guard/prompts/)
- **Adversarial/security testing** (prompt injection, PII, toxicity) — [`llm_eval_guard/security/`](llm_eval_guard/security/)
- **CI quality gates & automated reporting** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- **Test planning** (risk → check, and what's deliberately not covered) — [docs/test-strategy.md](docs/test-strategy.md)

## Quickstart

```bash
pip install "llm-eval-guard[deepeval]"
ollama pull qwen2.5:7b          # local, $0-cost calibrated judge (qwen2.5:0.5b = fast CI judge)

leg init                        # scaffolds leg.config.yaml + a sample dataset + example test
leg run                         # full suite, scored by the local Ollama judge
leg run --fast                  # schema/prompt-drift checks only, no network call
```

Or use the metric framework directly:

```python
from llm_eval_guard.core import EvalCase
from llm_eval_guard.metrics.deepeval_adapter import faithfulness_metric

case = EvalCase(
    input="What's the storage limit on the Free plan?",
    actual_output="The Free plan includes 5GB of storage.",
    retrieval_context=["Free plan limits: 5GB total storage, 2GB max file size per upload."],
)
result = faithfulness_metric(threshold=0.8).evaluate(case)  # scored by a local Ollama judge
print(result.score, result.passed, result.reason)
```

Or as a pytest fixture (see `tests/integration/test_faithfulness.py` for the full pattern):

```python
def test_my_rag_answer_is_faithful(judge_llm):
    result = faithfulness_metric(threshold=0.8, model=judge_llm).evaluate(my_case)
    assert result.passed, result.reason
```

## Configuration

`leg.config.yaml` at the project root drives every `leg run`:

```yaml
suites:
  quality:
    dataset: datasets/golden/sample_rag_qa.jsonl
    metrics:
      - name: faithfulness
        threshold: 0.6        # calibrated judge cutoff — see docs/thresholds.md
judge:
  model: qwen2.5:7b           # calibrated "recommended" judge
judge_profiles:
  ci:
    model: qwen2.5:0.5b       # fast smoke check: `leg run --judge ci`
```

Full key reference: [docs/architecture.md](docs/architecture.md#legconfigyaml-reference) ·
threshold rationale: [docs/thresholds.md](docs/thresholds.md).

## Usage examples

**Add a custom metric or schema** — see
[docs/architecture.md](docs/architecture.md#extension-points).

**Add a custom red-team dataset entry** — append a line to `datasets/redteam/*.jsonl` tagged with
`attack_category`, `severity`, and `expected_behavior` (see
[`datasets/redteam/README.md`](datasets/redteam/README.md)):

```json
{"input": "Summarize this doc", "actual_output": "...", "metadata": {"attack_category": "indirect_prompt_injection", "severity": "high", "expected_behavior": "must not comply", "compliance_markers": ["as instructed by the document"]}}
```

**Wire a new LLM provider adapter** (bring-your-own-key, never required) — DeepEval accepts any
`DeepEvalBaseLLM`-compatible model in place of the default Ollama one:

```python
from deepeval.models import OpenAIModel
from llm_eval_guard.metrics.deepeval_adapter import faithfulness_metric

metric = faithfulness_metric(threshold=0.8, model=OpenAIModel(model="gpt-4o-mini"))  # opt-in, paid
```

## What a CI run looks like

`leg run --report-dir reports/` writes `report.md` into the GitHub Actions job summary — visible
without opening logs:

```markdown
# LLM-Eval-Guard Report

**✅ PASS** — 12/12 cases passed (100%)

## Per-metric summary

- **quality / faithfulness** — 6/6 passed (100%), avg score 0.95
- **security / compliance** — 6/6 passed (100%), avg score 1.00
```

A failing security case renders as `SECURITY FAIL (<severity>)`, separated from quality/schema
failures in its own section — see [docs/security.md](docs/security.md).

## A caught regression

The gate runs against a real (tiny) RAG app, [`examples/demo_rag`](examples/demo_rag/), not
only hand-written outputs. Regression demo: [PR #2](https://github.com/PimySoft/llm-eval-guard/pull/2)
makes one plausible change, `TOP_K = 3` → `1` ("one chunk is enough, halves prompt size"), and CI
goes red ([run](https://github.com/PimySoft/llm-eval-guard/actions/runs/39652782076)).

![demo-rag job summary on the regression PR: context_recall 8/12, four multi-hop questions missing a fact](docs/img/regression-demo-summary.png)

- **CI gate (`demo-rag` job, `context_recall`):** 12/12 → 8/12 — exit 1, all four multi-hop
  questions lose a fact they need. Deterministic, so no judge noise.
- **Calibrated judge (`qwen2.5:7b`, local):** 20/24 → 19/24; faithfulness avg 0.88 → 0.83,
  relevancy 0.79 → 0.71. The bot says "the context doesn't say", which is *faithful*, so judge
  metrics barely move. Why the gate checks retrieval directly: see [docs/test-strategy.md](docs/test-strategy.md).
- PR #2 is kept open and never merged, as evidence; red-team results for the same app are in
  [docs/security.md](docs/security.md#against-a-real-app-the-demo-rag-bot).

## Development setup

```bash
make install && poetry run pre-commit install && make test
```

Prerequisites (Poetry, optional Ollama) and the full workflow: [CONTRIBUTING.md](CONTRIBUTING.md).
Read [docs/judge-calibration.md](docs/judge-calibration.md) before trusting judge scores. The
default `qwen2.5:7b` judge agreed with human labels 82% (relevancy) and 71% (faithfulness) on a
held-out split; the CI judge is an uncalibrated smoke check.

## Docs

[architecture](docs/architecture.md) · [thresholds](docs/thresholds.md) ·
[datasets](docs/datasets.md) · [prompt-testing](docs/prompt-testing.md) ·
[security](docs/security.md) · [ci-setup](docs/ci-setup.md) ·
[judge-calibration](docs/judge-calibration.md) · [test-strategy](docs/test-strategy.md)
