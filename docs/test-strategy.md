# Test strategy

What can go wrong when an LLM/RAG feature ships, which check covers it, and what's left out on
purpose. The system under test is `examples/demo_rag`; any app plugs in through a suite `generator`.

## Risks → checks

- **Retrieval regression** → `context_recall` (`demo` suite): every needed fact must be in the
  retrieved chunks. Deterministic, so it gates CI exactly. Why not leave it to the judge: an
  answer saying "the context doesn't cover that" is faithful, just useless ([README](../README.md#a-caught-regression)).
- **Hallucination** → `faithfulness`: the judge checks each claim against `retrieval_context`.
- **Off-topic answers** → `answer_relevancy`, scored separately: a grounded answer to the wrong
  question passes one and fails the other.
- **Broken output contract** → `SchemaValidationMetric` (strict), on every commit via `leg run --fast`.
- **Unreviewed prompt edits** → contract + drift-snapshot tests ([prompt-testing.md](prompt-testing.md)).
- **Direct injection / jailbreak** → `compliance` + `task_completion`: did it obey the attack,
  and did it still do the real task?
- **Indirect injection** → the same two, with the poison in `retrieval_context` ([security.md](security.md)).
- **PII leakage** → `pii_leakage` (regex).
- **Toxic output** → `toxicity` (judge, not calibrated against human labels).
- **A wrong judge** → calibration against hand-labeled cases ([judge-calibration.md](judge-calibration.md)).
  Every judge score is only as trustworthy as this.

## Prioritisation

- **Deterministic checks gate CI** (schema, drift, markers, regex, `context_recall`): $0,
  instant, never flaky, so a red build is always real.
- **Judge checks gate locally** on the calibrated judge; CI only smoke-tests the plumbing
  ([ci-setup.md](ci-setup.md#the-judge-in-ci)).
- **Zero tolerance for security**; quality uses calibrated cutoffs ([thresholds.md](thresholds.md)).
- **Fixed, versioned inputs:** a score change traces back to a code change, not new inputs.

## Not covered, on purpose

- **Correctness against `expected_output`:** faithfulness + relevancy catch the RAG failure modes
  without a reference answer, which real apps rarely have.
- **Paraphrased attacks:** markers are literal ([security.md](security.md#remaining-limits-of-marker-matching)).
- **Ranking quality** (MRR, nDCG): the generator sees all k chunks, so order barely matters.
- **Multi-turn conversations:** `EvalCase` is one question, one answer.
- **Latency, throughput, cost:** performance, not quality; everything is local anyway.
- **Non-English input, bias/fairness:** no labeled data; claiming coverage would be worse than
  stating the gap.
- **Generator non-determinism across machines:** the CI-gated metric reads retrieval, which is
  fully deterministic, for exactly this reason.
