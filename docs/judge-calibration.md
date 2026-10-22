# Judge Calibration

An LLM judge is unverified until it's checked against ground truth. `scripts/calibrate_judge.py`
measures that against the hand-labeled golden dataset.

## In short

- Default judge `qwen2.5:7b`, held-out agreement with human labels: relevancy **82%**,
  faithfulness **71%** (below the 80% bar, so gated at a lowered 70%).
- CI runs an uncalibrated `qwen2.5:0.5b` as a plumbing check only.
- Judge kappa (`test`): faithfulness **0.43**, relevancy **0.48**, i.e. moderate.
- Human self-agreement kappa is lower still (0.25 / 0.00, n=12), so the labels, not the judge,
  are now the weak link ([below](#human-ceiling)).

## How it works

The script scores [`sample_rag_qa.jsonl`](../datasets/golden/sample_rag_qa.jsonl) with the judge
and compares against `human_faithfulness`/`human_relevancy` ([datasets.md](datasets.md)):

- **Pass/fail agreement** (human label passes at ≥ 0.5), with a bootstrap 95% CI
- **Cohen's kappa** on pass/fail. Why: it removes chance agreement, which raw agreement
  over-credits when one class dominates
- **Mean absolute error** and **Pearson r**
- **Per-`failure_mode` agreement** and **seconds per case**

```bash
python scripts/calibrate_judge.py --model qwen2.5:7b --split dev     # tune/compare on dev
python scripts/calibrate_judge.py --model qwen2.5:7b --split dev \
  --faithfulness-threshold 0.6 --relevancy-threshold 0.5             # judge pass cutoffs
python scripts/calibrate_judge.py --split dev --json > result.json   # includes per-case scores
```

- Exits 1 if either metric's agreement is below `--min-agreement` (default 0.8).
- Tune on `dev` only; run `test` once, for the final choice. Why: agreement on tuning data is
  overstated.
- `DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE=300` avoids spurious timeouts on slower models.
- Why not just use the integration tests' pass rate: they only sample should-pass cases, so a
  rubber-stamping judge would look fine there.

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

Run once with the choice above; not re-tuned afterwards.

- **answer_relevancy — 82%** [59–100%], MAE 0.19, r 0.59, ~12 s/case. Clears the 80% bar.
- **faithfulness — 71%** [47–88%], MAE 0.24, r 0.58, ~22 s/case. **Below the 80% bar.**
- Faithfulness errors flipped direction vs `dev`: 4 of 8 correct (`none`) answers scored 0.0 or
  0.5, i.e. false rejections, plus 1 hallucinated detail let through at 0.67.
- n=17 is small — the interval spans 47–88%, so this neither confirms nor rules out an 80% judge.

## Gate decision: faithfulness at a lowered 70% bar

No local model cleared 80% held-out on faithfulness, so per plan.md the best one is gated at a
lowered, explicit bar instead of being quietly trusted:

- Faithfulness gates at **70%** (`MIN_PASS_RATE` in `tests/integration/test_faithfulness.py`);
  relevancy keeps 80%.
- Why 70% is defensible: `dev` 82%, `test` 71%, and the `test` interval (47–88%) includes 80%.
- Why it still catches regressions: gates use a suite pass *rate*, so per-case judge errors
  average out; a grounding regression shifts the whole rate, not one case.
- Human self-agreement kappa is 0.25 / 0.00, below the judge's ([Human ceiling](#human-ceiling)).
- Re-calibrate on a fresh, larger held-out set before raising this bar — not on this `test` split.

## Human ceiling

A judge can't be expected to agree with the labels more than humans agree with each other.

- Judge kappa, same frozen config and scores as above (re-run 2026-10-22 to add kappa only):
  - `dev`: faithfulness **0.63**, relevancy **0.55**
  - `test`: faithfulness **0.43**, relevancy **0.48**
- Relevancy `test` at 82% raw is below an always-pass judge (88%, only 2 of 17 cases should
  fail), but its kappa of 0.48 shows real skill: it rejects bad answers, at the cost of 3 false
  rejections.
- Human kappa to compare against, pass/fail, from `scripts/relabel_sample.py`
  ([datasets.md](datasets.md#label-agreement)):
  - Self-agreement: faithfulness **0.25**, relevancy **0.00** (n=12), below the judge
  - Inter-rater: **pending** a second labeler
- How to read it once filled: judge kappa near human kappa means the judge is at the ceiling, so
  better labels come before more judge tuning. Judge kappa well below means there is headroom.
- The human sample is 12 cases with 2 relevancy fails, so one flipped case moves relevancy kappa
  from 1.0 to about 0.6. Compare the order of magnitude, not decimals.

## Judge roles

- **`qwen2.5:7b`** (default `judge`) — the numbers above; use for local/self-hosted gating.
- **`qwen2.5:0.5b`** (`judge_profiles.ci`, `leg run --judge ci`) — fast and **uncalibrated**;
  judge-scored tests are strict `xfail`s under it. How CI uses it: [ci-setup.md](ci-setup.md#the-judge-in-ci).

## `qwen2.5:0.5b` failure modes (observed)

- **Boilerplate reasoning** — near-identical, self-contradictory reason text on unrelated cases
  ("...does not align with the retrieval context. The contradictions are not present...").
- **Verdict count doesn't track claim count** — 3 verdicts for both a 1-claim and a 2-claim case.
- **Fabricated facts in its reasoning** — justified a relevancy score by citing "Alibaba Cloud",
  which appears nowhere in the dataset.
