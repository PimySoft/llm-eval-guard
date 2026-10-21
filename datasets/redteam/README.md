# Red-team datasets

- One `EvalCase` per line (`input`, `actual_output`, optional `retrieval_context`, `metadata`),
  loaded via `llm_eval_guard.core.load_dataset_cases`.
- `actual_output` is a recorded response from a **properly-defended** pipeline — these files stay
  all-passing; see [docs/datasets.md](../../docs/datasets.md#why-shipped-datasets-stay-all-passing).
- Metrics that score them: [docs/security.md](../../docs/security.md).

## `metadata` keys

Required on every entry:

- `attack_category` (`str`) — `direct_prompt_injection`, `indirect_prompt_injection`,
  `jailbreak`, or `pii_leakage`
- `severity` (`str`) — `low`, `medium`, `high`, or `critical`
- `expected_behavior` (`str`) — one line describing the required safe behavior

Injection and jailbreak entries only:

- `compliance_markers` (`list[str]`) — substrings that mean the model *complied* with the attack
  if they appear in `actual_output`; read by `ComplianceMetric`
- `task_markers` (`list[str]`) — substrings expected if the model still did the real task; read
  by `TaskCompletionMetric`

`pii_leakage.jsonl` carries no `compliance_markers`/`task_markers`: `PIILeakageMetric` scans
`actual_output` directly for PII patterns absent from `input`/`retrieval_context`, no markers
needed.

## Files

- **`prompt_injection.jsonl`** — direct injection; the attacker is the user. Covers system-prompt
  exfiltration, fake overrides, format hijacking, and guardrail-disable requests.
- **`indirect_injection.jsonl`** — the attack hides in a poisoned retrieved document while the
  user's request stays benign. See
  [architecture.md](../../docs/architecture.md#indirect-prompt-injection--request-flow).
- **`jailbreak.jsonl`** — persona and role-play bypasses (DAN-style, fictional framing).
- **`pii_leakage.jsonl`** — probing questions that could elicit fabricated or leaked PII, plus
  false-positive fixtures (echoed PII, `example.com` placeholders).

## Provenance & licensing

Every entry is self-authored for this project, inspired by attack patterns documented publicly by
security research (e.g. OWASP's [LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/),
"LLM01: Prompt Injection") — none of this is copied from a licensed or third-party dataset.

All PII in `pii_leakage.jsonl` (names, emails, phone numbers) is synthetic and fictional; no real
personal data appears anywhere in this repo (see `CONTRIBUTING.md`). Jailbreak entries describe
*attack prompts* only — no entry contains real actionable harmful instructions, by design.
