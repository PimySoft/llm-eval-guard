# Prompt Template Testing

## Layout

- `prompts/{name}.j2` — the Jinja2 template, versioned in git.
- `prompts/{name}.meta.yaml` — sidecar metadata: `version`, `required_variables`, `max_length`
  (optional character budget), `sample_variables` (used by both the contract test and the drift
  snapshot below).
- `tests/fixtures/prompt_snapshots/{name}.txt` — the committed golden render.

**Why a sidecar file, not front-matter inside the `.j2`:** metadata is template *config*, not
prompt content — parsing it back out of Jinja comments would need a custom parser for no benefit.

## Contract tests (`tests/unit/test_prompt_registry.py`)

For every template in `prompts/`:
1. Renders with `sample_variables` without raising.
2. Raises `jinja2.UndefinedError` if a required variable is dropped — enforced by
   `Environment(undefined=StrictUndefined)`, not a manual check.
3. Stays under `max_length` characters.

**Why characters, not tokens:** token count is model-specific (needs a tokenizer per provider);
character length is a free, model-agnostic proxy that's good enough to catch a budget blowout
before it reaches a real token counter.

`PromptRegistry.load()` fails fast if `sample_variables` doesn't cover `required_variables` — that
mismatch would otherwise only surface later as a confusing `UndefinedError` from a test that
assumed the sample was complete.

## Drift detection (snapshots)

Each template's render (with its `sample_variables`) is compared against
`tests/fixtures/prompt_snapshots/{name}.txt`. A changed prompt — wording, structure, instructions —
fails the test with a unified diff.

```bash
pytest tests/unit/test_prompt_registry.py            # fails on drift
pytest tests/unit/test_prompt_registry.py --update-snapshots  # accept the new render
```

**Review workflow:** a snapshot diff in a PR is a prompt-behavior change — review it the same way
you'd review a code diff, not as generated-file noise to skip past.

## Adding a new template

1. Add `prompts/{name}.j2` + `prompts/{name}.meta.yaml`.
2. Run `pytest tests/unit/test_prompt_registry.py --update-snapshots` once to generate its
   snapshot — it fails on first run to force a deliberate review before committing.
3. Review and commit the generated `tests/fixtures/prompt_snapshots/{name}.txt`.
