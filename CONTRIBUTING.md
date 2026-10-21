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

- Python `>=3.10,<3.13`
- [Ollama](https://ollama.com) — optional; only `live_llm`-marked judge tests need it, and they
  auto-skip without it. `ollama pull qwen2.5:7b` (calibrated default; they pass under it), or
  `LEG_JUDGE_MODEL=qwen2.5:0.5b` for the fast CI judge (they're strict `xfail`s under it).
- Changed the judge model? Re-run `python scripts/calibrate_judge.py` — see
  [docs/judge-calibration.md](docs/judge-calibration.md).

## Common tasks

- `make lint` — Ruff lint
- `make format` — Ruff format
- `make typecheck` — mypy
- `make test` — pytest

## Adding a new metric adapter

See [docs/architecture.md](docs/architecture.md#extension-points).

## Adding red-team content

Every adversarial prompt added to `datasets/redteam/` must be tagged with `attack_category`,
`severity`, and `expected_behavior`, and must not contain real PII — synthetic data only. Schema:
[datasets/redteam/README.md](datasets/redteam/README.md).
