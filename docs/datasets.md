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

- `id` (`str`) — stable `rag-NNN` id; never reuse or renumber
- `split` (`dev | test`) — ~70/30, stratified by `failure_mode`
- `category` (`str`) — question shape: `single-fact`, `multi-hop`, `context-missing` (answer not
  in the retrieved chunks), `verbose`, `ambiguous`
- `failure_mode` (`str`) — what a correct judge should catch, or `none`:
  - `hallucinated-detail` — correct answer plus an invented, unasked-for specific
  - `contradiction` — a claim the retrieved context contradicts
  - `unsupported-claim` — context lacks the answer; the output asserts one anyway
  - `partially-grounded` — context answers part of the question; the output guesses the rest
  - `off-topic` — grounded, but doesn't address the question
  - `unhelpful-refusal` — declines although the context had the answer
- `human_faithfulness` (`float 0-1`) — human-reasoned faithfulness score, ground truth for
  [judge-calibration.md](judge-calibration.md)
- `human_relevancy` (`float 0-1`) — human-reasoned answer-relevancy score, ground truth for
  [judge-calibration.md](judge-calibration.md)
- `note` (`str`) — why this label, in one line

- Why two labels: an answer can be grounded but off-topic, or on-topic but hallucinated; one
  score would hide which regressed.
- Why a `dev`/`test` split: the judge is picked on `dev`; `test` is scored once, for the
  headline number.

### Labeling rules

- Scale: `1.0` all claims supported; `0.5` core answer right but overstated or resting on a
  plausible reading; `0.0` any material claim unsupported or contradicted
- A score ≥ 0.5 counts as pass, so `ambiguous` 0.5 cases are should-pass borderlines
- The first four failure modes fail faithfulness only; `off-topic`/`unhelpful-refusal` fail
  relevancy only — `tests/unit/test_dataset.py` enforces this, plus the pass/fail balance (40–60%
  should-fail) and that every mode appears in both splits
- Refusals that assert nothing about the product count as faithful

### Composition

56 cases, 28 should-pass / 28 should-fail, 39 `dev` / 17 `test`.

- Failure modes: 28 none, 6 hallucinated-detail, 6 contradiction, 6 unsupported-claim,
  4 partially-grounded, 4 off-topic, 2 unhelpful-refusal
- Categories: 25 single-fact, 15 multi-hop, 9 context-missing, 4 ambiguous, 3 verbose
- Several questions appear twice with a good and a bad answer (HIPAA, family plan, encryption,
  Free-plan Trash) so a judge can't pass by keying on the question

### Label agreement

- Ground truth is only as good as the labels: their consistency caps how good any judge can look
- Rubric for both labels, with a worked example per failure mode:
  [labeling-guide.md](labeling-guide.md)
- `scripts/relabel_sample.py` reports pass/fail agreement, Cohen's kappa, exact agreement, MAE and
  the differing ids per label. Why kappa: on a 50/50 pass/fail set, chance alone agrees 50%
- Every labeler gets the same blind sample (fixed seed): at least 20%, i.e. 12 cases, with no
  labels, notes, failure modes or expected outputs

Self-agreement (the original labeler, again):

- `python scripts/relabel_sample.py sample` writes `sample_rag_qa.relabel.jsonl`; a few days
  later, fill in both labels without opening the dataset, then `... score`
- Result: **not yet measured**

Inter-rater agreement (a second labeler, guide only):

- `... sample --labeler <name>` writes `sample_rag_qa.relabel.<name>.jsonl`; they label it using
  only [labeling-guide.md](labeling-guide.md), then `... score --labeler <name>`
- `... compare A.jsonl B.jsonl` compares any two filled-in files, e.g. the second labeler against
  your own re-label
- Review the differing ids together and fix the guide, never the `test` labels
- Result: **not yet measured** — record kappa per label and the guide changes it led to

## `datasets/golden/sample_tool_calls.jsonl`

- Five clean `ToolCallOutput`-shaped cases (`llm_eval_guard/schema/models.py`) feeding the
  `schema` suite — what `leg run --fast` exercises.
- `actual_output` is a JSON *string*, not answer text; `SchemaValidationMetric` parses it itself.

## Red-team datasets

See [`datasets/redteam/README.md`](../datasets/redteam/README.md).

## Why shipped datasets stay all-passing

They're the repo's own dogfood gate, and a real gate stays green. Failure detection is proven in
unit tests that build malformed or vulnerable variants in-process (`test_schema_validation.py`,
`test_cli.py`, `test_injection.py`, `test_pii.py`).
