# Datasets

## `datasets/golden/sample_rag_qa.jsonl`

One JSON object per line. Loaded via `llm_eval_guard.core.load_golden_dataset`.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `input` | `str` | yes | The user's question |
| `actual_output` | `str` | yes | The (recorded) answer being graded |
| `expected_output` | `str \| null` | no | Reference/ideal answer, for metrics that use it (e.g. contextual precision) |
| `retrieval_context` | `list[str] \| null` | no | Chunks the RAG pipeline retrieved for this input |
| `metadata` | `object` | no | Free-form; this dataset uses the keys below |

### `metadata` keys used by this dataset

| Key | Type | Meaning |
|---|---|---|
| `category` | `str` | `easy`, `hallucination`, `off-topic`, `appropriate-refusal`, `multi-hop`, `verbose-padding`, `unhelpful-refusal`, `ambiguous` |
| `human_faithfulness` | `float 0-1` | Human-reasoned faithfulness score — ground truth for [[judge-calibration]] |
| `human_relevancy` | `float 0-1` | Human-reasoned answer-relevancy score — ground truth for [[judge-calibration]] |
| `note` | `str` | Why this label, in one line |

**Why:** faithfulness and relevancy are labeled and scored *separately* because they catch
different failures — an answer can be grounded but off-topic (`off-topic` case), or on-topic but
hallucinated (`hallucination` cases). Collapsing them into one score would hide which failure mode
regressed.

15 cases, hand-labeled: 3 easy, 4 hallucination, 1 off-topic, 1 appropriate-refusal,
1 unhelpful-refusal, 1 verbose-padding, 1 ambiguous, 3 multi-hop — covering the easy/ambiguous/
adversarial-but-benign spread called for in plan.md Phase 2.5.
