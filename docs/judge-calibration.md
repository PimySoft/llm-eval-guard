# Judge Calibration

An LLM judge is itself an unverified component until it's checked against ground truth. Wiring
`FaithfulnessMetric` up to Ollama proves the *plumbing* works — it proves nothing about whether
the scores it returns are trustworthy. This is what `scripts/calibrate_judge.py` measures, and
what it found.

## How it works

`scripts/calibrate_judge.py` runs the configured judge model over every case in
[`datasets/golden/sample_rag_qa.jsonl`](../datasets/golden/sample_rag_qa.jsonl) and compares its
`faithfulness`/`answer_relevancy` scores against the hand-assigned `human_faithfulness` /
`human_relevancy` labels (see [datasets.md](datasets.md)). It reports:

- **Pass/fail agreement** — does the judge's pass/fail call (score ≥ 0.5) match the human label's?
- **Mean absolute error** — average `|human_score - judge_score|`
- **Pearson r** — do the judge's scores move with the human scores at all?

```bash
python scripts/calibrate_judge.py                          # default judge model
python scripts/calibrate_judge.py --model llama3.2:1b       # try a different judge
python scripts/calibrate_judge.py --min-agreement 0.8       # exit 1 if agreement falls short
```

**Why not just eyeball the example test suite's pass rate:** `tests/integration/test_faithfulness.py`
only samples cases already labeled "should pass" — it has no cases the judge is *supposed* to
reject. A judge that rubber-stamps everything as faithful would still look fine there. Calibration
is the only place the known-bad cases (hallucinations, off-topic answers) get checked.

## Result: `qwen2.5:0.5b` fails calibration

Measured against the 15-case golden set (`--min-agreement 0.8`, the default):

- **faithfulness** — agreement **40%**, MAE 0.59, Pearson r -0.21, n=15
- **answer_relevancy** — agreement **20%**, MAE 0.60, Pearson r -0.16, n=15

Both fail the 80% bar — badly. Negative Pearson r means the judge's scores are, if anything,
*inversely* related to the human labels on this set: not just noisy, actively unreliable.

**Why it's still the shipped default:** it's what runs in reasonable time on a free, CPU-only
Actions runner. It's never *silently* trusted — `calibrate_judge.py` exits 1 on it, and the
judge-scored integration tests are marked `xfail` with a pointer back here.

## Known failure modes (observed)

**Boilerplate, self-contradictory reasoning.** Across unrelated cases, the faithfulness judge
returned near-identical reason text regardless of input, including internally contradictory
phrasing:

> "The score is 0.67 because the actual output does not align with the information provided in
> the retrieval context. The contradictions are not present in the given information."

Same sentence, verbatim, on both a correct answer and a fabricated one — the model isn't
performing case-specific entailment checking at this size, just emitting a plausible-shaped
template.

**Verdict count doesn't track claim count.** Faithfulness decomposes an answer into claims, then
generates one verdict per claim. On a 1-claim case it returned 3 verdicts; on a 2-claim case, also
3. The judge isn't reliably tracking its own intermediate reasoning state.

**Fabricated domain facts in relevancy reasoning.** Grading a `sample_rag_qa.jsonl` case about
"Aperture Cloud Storage," the relevancy judge justified a score by asserting:

> "The Free plan is a basic version of Alibaba Cloud's services..."

Alibaba Cloud is never mentioned anywhere in the dataset — a fabricated association, not a typo.

**Net effect:** the judge doesn't discriminate between faithful and hallucinated answers — most
cases (good and bad alike) cluster around the same ~0.0/0.33/0.67 scores regardless of content,
which is exactly what near-zero/negative correlation means in practice.

## Recommendation

Don't trust `qwen2.5:0.5b` (or any judge) for real gating decisions without a calibration run that
clears your bar. To get a usable judge:

1. Re-run with a larger model: `python scripts/calibrate_judge.py --model llama3.2:3b`
   (untested; `llama3.2:1b` timed out on the CPU it was tried on).
2. Set `LEG_JUDGE_MODEL` to whatever passes, and re-run calibration whenever you change the model
   or prompt — model choice is a tuning decision this script backs with a number, not a guess.
3. If no local model clears the bar on your hardware, the bring-your-own-key adapters (OpenAI/
   Anthropic, opt-in only — see VISION.md) are the fallback, at the cost of leaving the $0 policy.
