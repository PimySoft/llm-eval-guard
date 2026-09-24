# Red-team datasets

One JSON object per line, loaded the same way as `datasets/golden/` (via
`llm_eval_guard.core.load_dataset_cases`). Every entry is an `EvalCase`: `input`, `actual_output`
(a recorded response from a **properly-defended** pipeline — these are regression fixtures, kept
all-passing on purpose, same rationale as `datasets/golden/sample_tool_calls.jsonl`), optional
`retrieval_context` (a simulated poisoned document for indirect-injection cases), and `metadata`.

**Where the failure modes are demonstrated instead:** `tests/unit/test_injection.py` and
`tests/unit/test_pii.py` construct "vulnerable" variants of these cases in-process
(`case.model_copy(update={"actual_output": ...})`) and assert the metrics catch them — so
detection is proven without ever putting a failing case in the repo's own dogfood
`leg.config.yaml` (see plan.md Phase 4, DoD).

## `metadata` keys

| Key | Type | Required | Meaning |
|---|---|---|---|
| `attack_category` | `str` | yes | `direct_prompt_injection`, `indirect_prompt_injection`, `jailbreak`, `pii_leakage` |
| `severity` | `str` | yes | `low`, `medium`, `high`, `critical` |
| `expected_behavior` | `str` | yes | One-line description of the required safe behavior |
| `compliance_markers` | `list[str]` | injection/jailbreak only | Substrings that, if present in `actual_output`, mean the model *complied* with the attack — read by `ComplianceMetric` |
| `task_markers` | `list[str]` | injection/jailbreak only | Substrings expected if the model still completed the real task — read by `TaskCompletionMetric` |

`pii_leakage.jsonl` carries no `compliance_markers`/`task_markers`: `PIILeakageMetric` scans
`actual_output` directly for PII patterns absent from `input`/`retrieval_context`, no markers
needed.

## Files

- `prompt_injection.jsonl` — direct injection: the attack is embedded in the user's own message
  (system-prompt exfiltration, fake system overrides, format hijacking, guardrail-disable requests).
- `indirect_injection.jsonl` — the attack is embedded in *retrieved* content (a poisoned
  document/support ticket/wiki page), simulating a compromised RAG source rather than a malicious
  user. **Why treat this separately from direct injection:** the attacker here isn't the person
  asking the question — the defense has to hold even when the user's own request is completely
  benign, which is a different threat model than "the user is attacking me."
- `jailbreak.jsonl` — persona/role-play bypass attempts (DAN-style, fictional framing).
- `pii_leakage.jsonl` — prompts that could elicit fabricated or leaked PII, plus false-positive
  regression fixtures (echoed PII, `user@example.com` placeholders).

## Provenance & licensing

Every entry is self-authored for this project, inspired by attack patterns documented publicly by
security research (e.g. OWASP's [LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/),
"LLM01: Prompt Injection") — none of this is copied from a licensed or third-party dataset.

All PII in `pii_leakage.jsonl` (names, emails, phone numbers) is synthetic and fictional; no real
personal data appears anywhere in this repo (see `CONTRIBUTING.md`). Jailbreak entries describe
*attack prompts* only — no entry contains real actionable harmful instructions, by design.
