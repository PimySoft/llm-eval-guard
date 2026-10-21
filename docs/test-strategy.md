# Test strategy

What can go wrong when an LLM/RAG feature ships, which check covers each risk, and what is
deliberately left out. The system under test is the demo app (`examples/demo_rag`); the same
checks apply to any app wired in through a suite `generator`.

## Risks → checks

- **Retrieval regression** (wrong or fewer chunks reach the prompt) → `context_recall`
  (`demo` suite): every fact a question needs must be in the retrieved context. Deterministic,
  so it gates CI (`demo-rag` job) exactly. Why not leave this to the judge: on the top-1
  regression demo, `context_recall` fell 12/12 → 8/12 while judge pass rate fell only 20/24 →
  19/24 — an answer saying "the context doesn't cover that" is faithful, just useless.
- **Hallucination / unsupported claims** → `faithfulness` (`quality`, `demo_quality`): judge
  checks each claim against `retrieval_context`. Calibrated: 71% held-out agreement.
- **Off-topic or non-answers** → `answer_relevancy`: 82% held-out agreement. Scored separately
  from faithfulness — a grounded answer to the wrong question passes one and fails the other.
- **Output-contract breakage** (malformed tool-call JSON) → `SchemaValidationMetric` (`schema`
  suite, strict mode), runs on every commit via `leg run --fast`.
- **Unreviewed prompt edits** → prompt contract + drift-snapshot tests (`prompts/`,
  [prompt-testing.md](prompt-testing.md)): a template change must be an explicit snapshot update.
- **Direct prompt injection / jailbreak** → `compliance` + `task_completion` (marker checks):
  did the model obey the attack, and did it still do the real task.
- **Indirect injection** (instructions hidden in a retrieved doc) → the same two metrics, with
  the poisoned doc in `retrieval_context` — a separate threat, see [security.md](security.md).
- **PII leakage** → `pii_leakage` (regex): PII in the answer with no source in input/context.
- **Toxic output** → `toxicity` (judge, not calibrated against human labels).
- **The judge itself being wrong** → calibration against hand-labeled golden cases, dev/test
  split, bootstrap CIs ([judge-calibration.md](judge-calibration.md)). Every judge score above is
  only as trustworthy as this number.

## Prioritisation

- **Deterministic checks gate CI** (schema, drift, markers, regex, `context_recall`): $0, instant,
  no flakiness — a red build is always a real finding.
- **Judge checks gate locally** with the calibrated `qwen2.5:7b`; CI runs them under a fast
  uncalibrated judge only as a plumbing smoke test ([ci-setup.md](ci-setup.md)).
- **Zero tolerance for security** (threshold 1.0): one successful attack is a regression, not a
  rate. Quality metrics use calibrated cutoffs instead ([thresholds.md](thresholds.md)).
- **Fixed-input regression over open-ended exploration:** the golden and red-team sets are small
  and versioned, so a score change is attributable to a code change, not to different inputs.

## Not covered, on purpose

- **Answer correctness against `expected_output`:** no exact/semantic-match metric. Why:
  faithfulness + relevancy catch the failure modes that matter for RAG without a reference
  answer per case, which a real app rarely has.
- **Paraphrased attacks:** marker checks miss compliance worded differently from the markers —
  a known false-negative class, see [security.md](security.md).
- **Ranking quality** (MRR, nDCG): `context_recall` checks presence in the top-k, not order. Why:
  the generator sees all k chunks, so order inside the window barely changes the answer.
- **Multi-turn conversations:** `EvalCase` is one question, one answer.
- **Latency, throughput, cost:** a performance concern, not a quality gate; everything is local.
- **Non-English input, bias/fairness:** no labeled data for either; claiming coverage without it
  would be worse than stating the gap.
- **Generator non-determinism across machines:** temperature 0 + fixed seed on one machine only;
  CI's gated metric reads retrieval, which is fully deterministic, for exactly this reason.
