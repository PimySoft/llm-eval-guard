# Datasets

## `datasets/golden/sample_rag_qa.jsonl`

One JSON object per line. Loaded via `llm_eval_guard.core.load_golden_dataset`.

- `input` (`str`, required) — the user's question
- `actual_output` (`str`, required) — the (recorded) answer being graded
- `expected_output` (`str | null`, optional) — reference/ideal answer, for metrics that use it
  (e.g. contextual precision)
- `retrieval_context` (`list[str] | null`, optional) — chunks the RAG pipeline retrieved for this
  input
- `metadata` (`object`, optional) — free-form; this dataset uses the keys below

### `metadata` keys used by this dataset

- `category` (`str`) — `easy`, `hallucination`, `off-topic`, `appropriate-refusal`, `multi-hop`,
  `verbose-padding`, `unhelpful-refusal`, `ambiguous`
- `human_faithfulness` (`float 0-1`) — human-reasoned faithfulness score, ground truth for
  [judge-calibration.md](judge-calibration.md)
- `human_relevancy` (`float 0-1`) — human-reasoned answer-relevancy score, ground truth for
  [judge-calibration.md](judge-calibration.md)
- `note` (`str`) — why this label, in one line

**Why:** faithfulness and relevancy are labeled and scored *separately* because they catch
different failures — an answer can be grounded but off-topic (`off-topic` case), or on-topic but
hallucinated (`hallucination` cases). Collapsing them into one score would hide which failure mode
regressed.

15 cases, hand-labeled: 3 easy, 4 hallucination, 1 off-topic, 1 appropriate-refusal,
1 unhelpful-refusal, 1 verbose-padding, 1 ambiguous, 3 multi-hop — covering the easy/ambiguous/
adversarial-but-benign spread called for in plan.md Phase 2.5.

## `datasets/golden/sample_tool_calls.jsonl`

Five clean `ToolCallOutput`-shaped cases (see `llm_eval_guard/schema/models.py`), feeding the
`schema` suite in `leg.config.yaml` — this is what `leg run --fast` exercises, so it's kept
all-passing on purpose (a real quality gate should stay green; it isn't the place to demonstrate
failure detection). `actual_output` here is a JSON *string*, not the RAG answer text the other
golden set uses — `SchemaValidationMetric` parses it itself.

**Where the failure modes are demonstrated instead:** `tests/unit/test_schema_validation.py` and
`tests/unit/test_cli.py` construct their own isolated malformed/extra-field/missing-field fixtures
in `tmp_path`, so the strict/lenient and pass/fail behavior is proven without ever putting a
failing case in the repo's own dogfood config.
