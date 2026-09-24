# LLM-Eval-Guard

> A CI/CD quality gate for LLM and RAG applications — scores outputs against quality, schema,
> and security metrics, and fails a pull request when thresholds aren't met.

Status: **Phase 2 (core metric framework) complete** — CLI not yet implemented. See
[VISION.md](VISION.md) for the project charter and [plan.md](plan.md) for the build roadmap.

## Quickstart

_The `leg` CLI is coming in Phase 3. For now, use the metric framework directly:_

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

## Development setup

Prerequisites:

- [Poetry](https://python-poetry.org/docs/#installation) — dependency management
- [Ollama](https://ollama.com) — local, $0-cost LLM judge (required for the `live_llm`-marked
  tests; everything else auto-skips them and stays green without it)
  ```bash
  ollama pull qwen2.5:0.5b
  ```

```bash
make install   # poetry install --extras deepeval
poetry run pre-commit install
make test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full dev workflow, and
[docs/judge-calibration.md](docs/judge-calibration.md) before trusting the default judge model's
scores — it's measured, not assumed, and the measurement isn't flattering.
