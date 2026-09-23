# Contributing

Solo portfolio project — kept lightweight, but run through the same checks CI will.

## Dev setup

```bash
# 1. Install Poetry (https://python-poetry.org/docs/#installation) if you don't have it
# 2. Install dependencies
poetry install

# 3. Install git hooks
poetry run pre-commit install

# 4. Confirm everything works
make test
```

Requires Python `>=3.10,<3.13`. Requires [Ollama](https://ollama.com) installed locally with a
pulled model (`ollama pull llama3.2:3b`) to run the live judge-model test suite — unit tests do
not need it.

## Common tasks

| Command | Does |
|---|---|
| `make lint` | Ruff lint |
| `make format` | Ruff format |
| `make typecheck` | mypy |
| `make test` | pytest |

## Adding a new metric adapter

Implement `llm_eval_guard.core.metric.Metric` and normalize the underlying engine's result into
`MetricResult`. See `llm_eval_guard/metrics/deepeval_adapter.py` once Phase 2 lands.

## Adding red-team content

Every adversarial prompt added to `datasets/redteam/` must be tagged with `attack_category`,
`severity`, and `expected_behavior`, and must not contain real PII — synthetic data only.
