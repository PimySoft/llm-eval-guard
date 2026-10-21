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
1 unhelpful-refusal, 1 verbose-padding, 1 ambiguous, 3 multi-hop.

## `datasets/golden/sample_tool_calls.jsonl`

- Five clean `ToolCallOutput`-shaped cases (`llm_eval_guard/schema/models.py`) feeding the
  `schema` suite — what `leg run --fast` exercises.
- `actual_output` is a JSON *string*, not answer text; `SchemaValidationMetric` parses it itself.

## Red-team datasets

See [`datasets/redteam/README.md`](../datasets/redteam/README.md).

## Why shipped datasets stay all-passing

`sample_tool_calls.jsonl` and `datasets/redteam/` are the repo's own dogfood gate, and a real gate
should stay green. Failure detection is proven in unit tests instead, which build malformed or
vulnerable variants in-process (`test_schema_validation.py`, `test_cli.py`, `test_injection.py`,
`test_pii.py`).
