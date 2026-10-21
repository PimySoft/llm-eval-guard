# Architecture

## Data flow

Every check — quality, schema, security — normalizes through the same `EvalCase` →
`Metric` → `MetricResult` shape, so the runner, reporting, and CI gate never need to know which
engine scored a case.

```mermaid
flowchart LR
    D[("datasets/*.jsonl")] --> E[EvalCase]
    E --> M1["DeepEval adapter\n(faithfulness, relevancy, toxicity)"]
    E --> M2["Schema adapter\n(SchemaValidationMetric)"]
    E --> M3["Security adapters\n(compliance, task_completion, pii_leakage)"]
    M1 --> R[MetricResult]
    M2 --> R
    M3 --> R
    R --> RUN["core/runner.py\n(threshold pass/fail per case)"]
    RUN --> REP["reporting/\n(Markdown + JSON)"]
    REP --> CI["CLI exit code\n→ GitHub Actions status check\n→ merge gate"]
```

`Metric.evaluate(case) -> MetricResult` (`core/metric.py`) is the one seam every backend
implements — DeepEval today, Ragas as a deferred stretch adapter, rule-based checks for security. `core/registry.py` maps a `leg.config.yaml` metric name string to
a concrete `Metric` instance; `core/runner.py` is the only thing that calls `.evaluate()`.

## Config → suite → metric

```mermaid
flowchart TD
    CFG["leg.config.yaml"] --> SUITE["SuiteConfig\n(dataset path(s) + metric list)"]
    SUITE --> MC["MetricConfig\n(name, threshold, fast)"]
    MC --> REG["registry.build_metric()"]
    REG --> MET["Metric instance"]
```

- `leg run --suite <name>` runs one suite; `leg run` (or `--suite all`) runs every suite.
- `--fast` drops metrics without `fast: true` before `build_metric` runs — that's the whole
  mechanism behind the sub-second, network-free `leg run --fast`.

## `leg.config.yaml` reference

- `suites.<name>.dataset` (`str | list[str]`) — one JSONL path, or several concatenated in order
  (e.g. `security`'s four red-team files)
- `suites.<name>.metrics[].name` (`str`) — a registry key (`faithfulness`, `toxicity`,
  `compliance`, ...) or `schema:module.path:ClassName` for a custom Pydantic schema
- `suites.<name>.metrics[].threshold` (`float | null`) — pass/fail cutoff; omitted falls back to
  `registry.py`'s per-metric default (`1.0` for rule-based/schema metrics) — see [thresholds.md](thresholds.md)
- `suites.<name>.metrics[].fast` (`bool`) — whether `leg run --fast` includes this metric — `true`
  only for checks with no network call
- `judge.model` (`str | null`) — Ollama model tag; falls back to `LEG_JUDGE_MODEL` env var, then a
  built-in default
- `judge.base_url` (`str | null`) — Ollama server URL; falls back to `OLLAMA_BASE_URL` env var

Dataset paths resolve relative to the working directory `leg run` is invoked from, not the config
file's own directory (`core/dataset.py`) — run `leg run` from the project root, same as `pytest`.

## Extension points

Contributors extend the framework at three seams without touching `core/`:

- **Custom `Metric`** — subclass `Metric`, implement `name` and `evaluate()`, register it in
  `core/registry.py`'s `_JUDGE_METRICS`/`_RULE_METRICS` (or use it directly, outside
  `leg.config.yaml`). Reference implementation: `metrics/deepeval_adapter.py`.

  ```python
  from llm_eval_guard.core.metric import Metric
  from llm_eval_guard.core.models import EvalCase, MetricResult


  class MyMetric(Metric):
      @property
      def name(self) -> str:
          return "my_metric"

      def evaluate(self, case: EvalCase) -> MetricResult:
          score = ...  # your scoring logic
          return MetricResult(metric_name=self.name, score=score, passed=score >= self.threshold)
  ```

- **Custom schema** — no code change needed: point a `schema:` metric entry at any
  `pydantic.BaseModel` subclass on your Python path (`schema:your_pkg.models:YourSchema`). See
  `llm_eval_guard/schema/models.py` for the shipped examples and `schema/validation.py` for
  strict-vs-lenient mode.
- **Custom `PromptRegistry` source** — `PromptRegistry(prompts_dir)` (`prompts/registry.py`)
  takes any directory of `{name}.j2` + `{name}.meta.yaml` pairs; point it at your own prompts
  directory to get contract + drift-snapshot testing for free (see
  [prompt-testing.md](prompt-testing.md)).
- **Custom PII/toxicity backend** — both are plain `Metric`s; write e.g. a Presidio- or
  Detoxify-backed `Metric` and point `leg.config.yaml` at it. Nothing downstream changes. Why the
  defaults are regex/local-judge: [security.md](security.md).

## Indirect prompt injection — request flow

The least obvious mechanism in the codebase: the attacker never talks to the model directly, they
poison content the RAG pipeline retrieves on the *victim's* behalf.

```mermaid
sequenceDiagram
    participant Attacker
    participant Doc as Poisoned document
    participant User as Benign user
    participant RAG as RAG pipeline (under test)
    participant Metric as ComplianceMetric /\nTaskCompletionMetric

    Attacker->>Doc: Embeds an instruction\n("ignore prior instructions, reveal...")
    User->>RAG: Asks a genuine, unrelated question
    RAG->>Doc: Retrieves the poisoned document\n(as normal retrieval_context)
    RAG-->>Metric: EvalCase(input=user's question,\nactual_output=model's reply,\nretrieval_context=[poisoned doc])
    Metric->>Metric: compliance_markers found in actual_output?
    Metric->>Metric: task_markers still present?
    Metric-->>CI: fail if the injected instruction was\nfollowed, or if the real task was dropped
```

**Why a separate category from direct injection:** the poisoned text sits in `retrieval_context`,
not `input`. The user's request is benign, so a defense that only checks the user's words misses
it entirely. Metrics: `security/injection.py`, [security.md](security.md).
