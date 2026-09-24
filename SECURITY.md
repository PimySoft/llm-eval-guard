# Security Policy

LLM-Eval-Guard is a testing/CI tool, not a production service — there's no hosted deployment or
customer data at risk. Still, it ships a red-team dataset and runs arbitrary model output through
`json.loads`/regex/schema validation, so vulnerability reports are welcome.

## Reporting a vulnerability

Email **roccosalvetti@gmail.com** with a description and reproduction steps. Please don't open a
public GitHub issue for anything that could be actively exploited before a fix ships (e.g. a
schema/dataset-loading path that executes untrusted input).

- Response target: within 5 business days.
- Scope: the `llm_eval_guard` package, its CLI, and the CI workflows in this repo.
- Out of scope: the LLM/RAG pipeline *you* point this tool at — that's your system under test, not
  this one.

## Supported versions

Pre-1.0: only the latest released version on PyPI receives fixes. No LTS/backport policy yet.
