# VISION.md — LLM-Eval-Guard

## Problem statement

Teams shipping LLM/RAG features have no equivalent of a unit-test gate: a bad prompt change,
a broken retrieval step, or a regressed output schema merges silently because nothing fails
CI. LLM-Eval-Guard is a drop-in pytest-based quality gate that scores LLM/RAG outputs against
quality, schema, and security metrics and fails the build when scores drop below configured
thresholds — the same discipline `pytest --cov` gives regular code, applied to model outputs.

## Target user

ML/platform engineers who own an LLM or RAG feature in production and want CI to catch
faithfulness regressions, broken output contracts, and prompt-injection exposure before merge
— without standing up a hosted eval platform or paying per-call judge fees.

## Non-goals

- Not a full observability/tracing platform (no live production monitoring, no dashboards beyond CI reports) — use LangSmith, Arize, or Grafana for that.
- Not a hosted product — runs entirely in the user's own CI, no SaaS backend, no account required.
- Not a prompt-engineering IDE — it tests prompts/outputs, it doesn't help author them.
- Not a replacement for DeepEval/Ragas — it's a CI-gating and reporting layer built on top of one.

## Architectural decisions (locked for Phase 1+)

- **Primary interface:** Python package `llm_eval_guard`, a CLI (`leg run`, `leg init`), and a
  pytest plugin.
  Why: the CLI serves CI and scripts; the plugin lets teams write `assert result.passed` in their
  own test suite.
- **Default LLM provider:** local Ollama, required for v1.
  Why: keeps the $0 policy real — no contributor or CI run needs a paid key to pass.
- **Bring-your-own-key providers:** OpenAI/Anthropic adapters, opt-in only.
  Why: faster, better judging for those who want it, never required.
- **Evaluation engine:** DeepEval only for v1; Ragas is a stretch adapter, added after DeepEval
  works end-to-end.
  Why: depth on one engine beats two half-finished ones; the `Metric` interface leaves room for
  Ragas without a rewrite.
- **License:** Apache-2.0.
  Why: explicit patent grant, standard for infra tools, safe to adopt inside a company.
- **Package name:** `llm-eval-guard`, confirmed free on PyPI.

## Skills demonstrated

All target skills shipped — see [README.md](README.md#why).

## Cost policy

$0, no exceptions. Local Ollama judge by default, no cloud telemetry, public GitHub repo for
unlimited free Actions minutes. Full detail in `plan.md` under "Cost policy."
