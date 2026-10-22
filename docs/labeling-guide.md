# Labeling Guide

How to score `human_faithfulness` and `human_relevancy` on
[`sample_rag_qa.jsonl`](../datasets/golden/sample_rag_qa.jsonl). A second labeler should need
nothing but this page and the blind file from `scripts/relabel_sample.py sample`.

- Why a written guide: a second labeler can't agree with rules that only exist in one person's head.
- The worked examples below use an invented product, not dataset cases. Why: a guide quoting real cases would
  hand the labeler some of the answers and inflate agreement.

## Per-case checklist

Run through this for every case; the sections below explain each rule.

1. Read the question, then the context, then the answer.
2. Split the answer into claims. For each claim, find the sentence in the context that states it.
3. Look hardest at the claims that are easiest to miss next to correct ones:
   - a feature or limit assigned to the wrong plan ("on every plan" when the context names one)
   - comparatives and superlatives ("cheapest", "fastest", "best on the market")
   - numbers, durations and dropped qualifiers ("during business hours", "members only")
4. Faithfulness:
   - any claim with no supporting sentence, or a contradicting one: `0.0`, however good the rest
   - every claim stated: `1.0`; one stretched, or chunks disagree and the answer follows one: `0.5`
   - no product claims at all (refusal, "the docs don't say"): `1.0`, even if the refusal was
     wrong; that's relevancy's job
5. Relevancy, `0` or `1`: did it answer the question asked? Declining when the context has the
   answer is `0`; answering a different question is `0`, even if every word is true.
6. Score the two labels separately. A bad answer on one doesn't lower the other.

## Before you start

- Label from the blind file only. Don't open the dataset, git history, notes or judge output.
- Don't discuss cases with anyone until both label sets are scored.
- Score the two labels independently. A wrong answer can still be relevant; an on-topic answer can
  still be unfaithful.
- Judge against `retrieval_context` only, never against what you know about the product or the
  world. The context is the only source the answer was allowed to use.
- If you hesitate on a case, still pick a score. Write down its id and why, for the review.

## `human_faithfulness`: is every claim supported by the context?

1. List each claim the answer makes about the product (prices, limits, features, behavior).
2. Ignore filler and generic advice ("great question", "act quickly"). They aren't product claims.
3. Check each claim against the chunks, then score:

- `1.0`: every claim is stated in the context (paraphrase is fine)
- `0.5`: every claim comes from the context, but one is stretched. It drops a qualifier, rests on
  a plausible but unstated reading, or follows one chunk where two chunks disagree
- `0.0`: any material claim has no source in the context, or the context contradicts it
- An answer that asserts nothing about the product scores `1.0`, including "I don't know" and
  "the docs don't say". Unhelpfulness is a relevancy problem, not a faithfulness one
- Material means a user could act on it. One correct claim does not offset one invented claim
- The `0.5` vs `0.0` test: can you point to the sentence in the context the claim stretches?
  Yes means `0.5`. No sentence at all means `0.0`

## `human_relevancy`: does the answer address the question asked?

- `1.0`: it answers the question, whether or not the answer is true, padded or partly wrong
- `1.0`: it explains that the context doesn't cover the question, when the context really doesn't
- `0.0`: it talks about something else, even if what it says is true
- `0.0`: it declines or says "not found" although the context contains the answer
- Relevancy is effectively pass/fail in this dataset. Use `0.5` only if you can say why neither
  end fits, and flag the case

## Worked examples, one per failure mode

All examples use one invented bike-share context, unrelated to the dataset's product: "Day pass:
$8, unlimited 30-minute rides. Annual membership: $90/year, unlimited 45-minute rides. Rides over
the limit cost $3 per extra 15 minutes. E-bikes cost $0.20/minute extra, members only."

- **`none`**: Q "How much is a day pass?" A "$8, with unlimited 30-minute rides."
  - Faithfulness `1.0`, relevancy `1.0`
- **`none`, borderline**: Q "Can I ride an e-bike?" A "Yes, e-bikes cost $0.20/minute extra."
  - Faithfulness `0.5`: the price is stated, but the answer drops "members only", so it overstates
    for a day-pass holder. Relevancy `1.0`
- **`hallucinated-detail`**: Q "How much is membership?" A "$90/year for unlimited 45-minute
  rides, plus a free helmet."
  - Faithfulness `0.0`: the helmet appears nowhere. The correct price doesn't save it.
    Relevancy `1.0`
- **`contradiction`**: Q "How long can members ride?" A "Up to 60 minutes per ride."
  - Faithfulness `0.0`: the context says 45. Relevancy `1.0`
- **`unsupported-claim`**: Q "Can I pause my membership?" A "Yes, for up to 3 months a year."
  - Faithfulness `0.0`: pausing isn't in the context at all. Relevancy `1.0`
  - Contrast: "The docs don't mention pausing" scores `1.0`/`1.0`
- **`partially-grounded`**: Q "What does overtime cost, and is there a daily cap?" A "$3 per extra
  15 minutes, capped at $20 a day."
  - Faithfulness `0.0`: the rate is grounded, but the cap is a guess at the unanswered half.
    Relevancy `1.0`
- **`off-topic`**: Q "How much is a day pass?" A "Annual membership is $90/year."
  - Faithfulness `1.0`: true to the context. Relevancy `0.0`: it doesn't answer about day passes
- **`unhelpful-refusal`**: Q "What does overtime cost?" A "I couldn't find overtime pricing."
  - Faithfulness `1.0`: asserts nothing about the service. Relevancy `0.0`: the rate was there

## After scoring

- Run `scripts/relabel_sample.py score --labeler <name>`. It prints agreement, kappa and the ids
  where the labels differ.
- Review the differing ids together and decide which rule in this guide was missing or unclear.
  Fix the guide, not the dataset's `test` labels. Procedure: [datasets.md](datasets.md#label-agreement)
