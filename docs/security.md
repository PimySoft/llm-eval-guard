# Security & red-teaming

`leg run --suite security` scores every case in `datasets/redteam/*.jsonl` against four metrics
and fails the build on any single violation — rule-based metrics use `threshold: 1.0`, zero
tolerance, not a pass rate (see [thresholds.md](thresholds.md)).

Attack categories, files, and the dataset schema: [datasets/redteam/README.md](../datasets/redteam/README.md).
Indirect-injection request flow: [architecture.md](architecture.md#indirect-prompt-injection--request-flow).

## Metrics

- **`ComplianceMetric`** (`security/injection.py`) — fails if `actual_output` contains any of the
  case's `metadata.compliance_markers` — did the model do what the attack asked.
- **`TaskCompletionMetric`** (`security/injection.py`) — fails if none of `metadata.task_markers`
  appear — did the model still answer the real question.
- **`ToxicityMetric`** (`metrics/deepeval_adapter.py`) — DeepEval's judge-scored toxicity, on the
  same local Ollama model faithfulness/relevancy already use.
- **`PIILeakageMetric`** (`security/pii.py`) — regex-scans `actual_output` for PII absent from
  `input`/`retrieval_context`; `example.com`/`.org`/`.net` are allowlisted as placeholders.

## Design choices

- **Why rule-based markers, not an LLM judge, for compliance/task-completion:** each entry already
  encodes what compliance looks like — a $0, instant, deterministic string check beats a slower,
  noisier judge answering the same yes/no question.
- **Why regex, not Presidio, for PII:** the attack shapes (emails, phones, SSNs, cards) are
  pattern-regular; a bundled spaCy NER model is a poor size trade for the marginal recall.
  PII *echoed* from input/context passes; PII with no source in the case fails.
- **Why toxicity reuses the DeepEval/Ollama judge, not Detoxify:** no second model to install or
  calibrate. It inherits the judge's calibration caveat, so its integration tests are
  `xfail(strict=False)` — see [judge-calibration.md](judge-calibration.md).

## Proving the detectors discriminate

The shipped datasets are the *defended* case (kept all-passing — see
[datasets.md](datasets.md#why-shipped-datasets-stay-all-passing)). `tests/unit/test_injection.py`
and `test_pii.py` build *vulnerable* variants in-process and assert the metrics catch them.

## Reporting

- Console: a `security` failure renders as bold-red `SECURITY FAIL (<severity>)`, plus a closing
  `N security finding(s) — blocking by default` line.
- `report.md` (`leg run --report-dir`): a dedicated "Security findings" table, sorted by severity,
  separate from "Failing cases" — see [ci-setup.md](ci-setup.md#reports).
