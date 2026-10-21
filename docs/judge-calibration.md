# Judge Calibration

An LLM judge is itself an unverified component until it's checked against ground truth. Wiring
`FaithfulnessMetric` up to Ollama proves the *plumbing* works — it proves nothing about whether
the scores it returns are trustworthy. This is what `scripts/calibrate_judge.py` measures, and
what it found.

## How it works

`scripts/calibrate_judge.py` scores the cases in
[`datasets/golden/sample_rag_qa.jsonl`](../datasets/golden/sample_rag_qa.jsonl) with the judge and
compares against the hand-assigned `human_faithfulness`/`human_relevancy` labels (see
[datasets.md](datasets.md)). It reports:

- **Pass/fail agreement** — does the judge's pass/fail call match the human label's (human label
  passes at ≥ 0.5)? Plus a bootstrap 95% confidence interval.
- **Mean absolute error** — average `|human_score - judge_score|`
- **Pearson r** — do the judge's scores move with the human scores at all?
- **Per-`failure_mode` agreement** and **seconds per case**

```bash
python scripts/calibrate_judge.py --model qwen2.5:7b --split dev     # tune/compare on dev
python scripts/calibrate_judge.py --model qwen2.5:7b --split dev \
  --faithfulness-threshold 0.6 --relevancy-threshold 0.5             # judge pass cutoffs
python scripts/calibrate_judge.py --split dev --json > result.json   # includes per-case scores
```

- Exits 1 if either metric's agreement is below `--min-agreement` (default 0.8).
- Split discipline: compare models and tune cutoffs on `dev` only; run `test` once, for the final
  choice. **Why:** reporting agreement on the data it was tuned on would overstate it.
- `DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE=300` avoids spurious timeouts on slower models.

**Why not just eyeball the example test suite's pass rate:** `tests/integration/test_faithfulness.py`
only samples cases already labeled "should pass". A judge that rubber-stamps everything would
still look fine there; calibration is where the known-bad cases get checked.

## Model comparison (`dev`, n=39, Apple M3 GPU)

At the original 0.5 judge cutoff for both metrics:

- `qwen2.5:0.5b` — faithfulness 49% [33–64%], relevancy 26% [13–41%], ~1.5 s/case
- `llama3.2:1b` — did not finish: one judge call hung past a 300 s timeout
- `qwen2.5:3b` — faithfulness 51% [36–67%] (r −0.26), relevancy 46% [31–62%], ~8 s/case
- `phi3:mini` — faithfulness 56% [41–72%], relevancy 49% [33–64%], ~11 s/case
- `llama3.2:3b` — faithfulness 67% [51–82%], relevancy 67% [51–79%], ~5–7 s/case
- `qwen2.5:7b` — faithfulness 64% [49–79%], relevancy **87%** [74–97%], ~14–18 s/case

`qwen2.5:7b` reproduced the same 64%/87% on a second run. Every model accepted good answers but
missed contradictions and hallucinated details on faithfulness.

## Judge cutoff tuning (`dev`)

Sweeping the judge cutoff (0.5–1.0) for the top two models, from per-case scores:

- `qwen2.5:7b` faithfulness — 64% at 0.5, **82%** at 0.6, 79% at 0.7, 74% at 0.8
- `qwen2.5:7b` relevancy — **87%** at 0.5, 72% at 0.6, 64% at 0.8
- `llama3.2:3b` — best at 0.5 for both (67%); higher cutoffs only got worse

Why the cutoffs differ per metric:

- **Faithfulness over-credits half-grounded answers.** Wrong answers cluster at exactly 0.5 (one
  of two claims supported); good answers are mostly 1.0, with no case between 0.5 and 0.67. A 0.6
  cutoff ("more than half the claims supported") sits in that gap rather than on a single case.
- **Relevancy under-scores good answers.** Many correct, on-topic answers score 0.33–0.5, so any
  cutoff above 0.5 starts failing them.

## Chosen judge (fixed on `dev`, before the `test` run)

- Model `qwen2.5:7b`; judge cutoffs: faithfulness 0.6, answer_relevancy 0.5
- `dev`: faithfulness **82%** [69–92%], MAE 0.30, r 0.50; relevancy **87%** [74–97%], MAE 0.21,
  r 0.63
- Weakest faithfulness categories: `unsupported-claim` 50% (n=4), `partially-grounded` 67% (n=3)

## Held-out result (`test`, n=17)

Pending — run once with the choice above.

## `qwen2.5:0.5b` failure modes (observed)

- **Boilerplate reasoning** — near-identical, self-contradictory reason text on unrelated cases
  ("...does not align with the retrieval context. The contradictions are not present...").
- **Verdict count doesn't track claim count** — 3 verdicts for both a 1-claim and a 2-claim case.
- **Fabricated facts in its reasoning** — justified a relevancy score by citing "Alibaba Cloud",
  which appears nowhere in the dataset.
