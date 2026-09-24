# Contributing

Solo portfolio project — kept lightweight, but run through the same checks CI will.

## Dev setup

```bash
# 1. Install Poetry (https://python-poetry.org/docs/#installation) if you don't have it
# 2. Install dependencies (incl. the deepeval extra)
make install

# 3. Install git hooks
poetry run pre-commit install

# 4. Confirm everything works
make test
```

Requires Python `>=3.10,<3.13`. Requires [Ollama](https://ollama.com) installed locally with a
pulled model (`ollama pull qwen2.5:0.5b`, or set `LEG_JUDGE_MODEL` to use another one) to run the
`live_llm`-marked judge-model tests — everything else auto-skips them and stays green without
Ollama installed. Re-run `python scripts/calibrate_judge.py` after changing the judge model (see
docs/judge-calibration.md).

## Common tasks

| Command | Does |
|---|---|
| `make lint` | Ruff lint |
| `make format` | Ruff format |
| `make typecheck` | mypy |
| `make test` | pytest |

## Adding a new metric adapter

Implement `llm_eval_guard.core.metric.Metric` and normalize the underlying engine's result into
`MetricResult`. See `llm_eval_guard/metrics/deepeval_adapter.py` for the reference implementation.

## Adding red-team content

Every adversarial prompt added to `datasets/redteam/` must be tagged with `attack_category`,
`severity`, and `expected_behavior`, and must not contain real PII — synthetic data only.
