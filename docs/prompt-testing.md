# Prompt Template Testing

## Layout

- `prompts/{name}.j2` — the Jinja2 template, versioned in git.
- `prompts/{name}.meta.yaml` — sidecar metadata: `version`, `required_variables`, `max_length`
  (optional character budget), `sample_variables` (used by both the contract test and the drift
  snapshot below).
- `tests/fixtures/prompt_snapshots/{name}.txt` — the committed golden render.

Why a sidecar, not front-matter in the `.j2`: metadata is config, not prompt content, and
parsing it out of Jinja comments would need a custom parser.

## Contract tests (`tests/unit/test_prompt_registry.py`)

Every template in `prompts/` must:

1. Render with `sample_variables` without raising.
2. Raise `jinja2.UndefinedError` when a required variable is dropped (`StrictUndefined`).
3. Stay under `max_length` characters.

- Why characters, not tokens: token counts need a tokenizer per provider; length is a free,
  model-agnostic proxy that still catches a budget blowout.
- `PromptRegistry.load()` fails fast if `sample_variables` doesn't cover `required_variables`,
  instead of a confusing `UndefinedError` later.

## Drift detection (snapshots)

Each template's render is compared against its committed snapshot; any change fails with a
unified diff.

```bash
pytest tests/unit/test_prompt_registry.py            # fails on drift
pytest tests/unit/test_prompt_registry.py --update-snapshots  # accept the new render
```

A snapshot diff in a PR is a prompt-behavior change: review it like code, not as generated noise.

## Adding a new template

1. Add `prompts/{name}.j2` + `prompts/{name}.meta.yaml`.
2. Run `pytest tests/unit/test_prompt_registry.py --update-snapshots` to generate its snapshot
   (a plain run fails first, forcing a deliberate review).
3. Review and commit the generated `tests/fixtures/prompt_snapshots/{name}.txt`.
