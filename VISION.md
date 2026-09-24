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

- Not a full observability/tracing platform (no live production monitoring, no dashboards beyond CI reports) — see [Grafana/LangSmith/Arize] for that.
- Not a hosted product — runs entirely in the user's own CI, no SaaS backend, no account required.
- Not a prompt-engineering IDE — it tests prompts/outputs, it doesn't help author them.
- Not a replacement for DeepEval/Ragas — it's a CI-gating and reporting layer built on top of one.

## Architectural decisions (locked for Phase 1+)

| Decision | Choice | Why |
|---|---|---|
| Primary interface | Python package `llm_eval_guard`, CLI (`leg run`, `leg init`) + pytest plugin entry point | CLI for CI/scripted use, pytest plugin so teams can write `assert rag_case.faithfulness_score >= 0.8` directly in their own test suite |
| Default LLM provider | **Ollama (local)** is the required path for v1 | Keeps the $0 cost policy real — no contributor or CI run needs a paid key to get a passing build |
| Bring-your-own-key providers | OpenAI/Anthropic adapters, documented as opt-in only | Faster/higher-quality judging for users who want it, never required to run the suite |
| Evaluation engine | **DeepEval** as the sole adapter for v1; Ragas is a stretch second adapter, added only after DeepEval path is complete end-to-end | Depth on one engine demos better than two half-finished integrations; a thin internal `Metric` interface keeps the door open for Ragas later without a rewrite |
| License | Apache-2.0 | OSS tooling license with an explicit patent grant — standard for infra tools, signals it's safe to adopt inside a company |
| Package name | `llm-eval-guard` | Confirmed available on PyPI (no existing project at this name) |

## Skills Demonstrated (build toward this — final table ships in README Phase 6.1)

- [x] Metric-based LLM/RAG evaluation (faithfulness, answer relevancy) — Phase 2
- [x] Judge calibration / meta-evaluation against human-labeled ground truth — Phase 2.6
- [x] Schema/contract testing for structured LLM output — Phase 3.1
- [x] Regression testing via prompt-drift snapshots — Phase 3.2
- [ ] Adversarial/red-team testing: prompt injection (direct + indirect), jailbreaks, PII, toxicity — Phase 4
- [ ] CI quality gates with threshold enforcement and automated PR reporting — Phase 5

## Cost policy

$0, no exceptions. Local Ollama judge by default, no cloud telemetry, public GitHub repo for
unlimited free Actions minutes. Full detail in `plan.md` under "Cost policy."
