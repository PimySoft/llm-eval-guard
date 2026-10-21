# Demo RAG app (system under test)

A tiny support bot for a fictional product, "Acme Cloud Drive" — the real system the Phase 9 gate
scores, instead of hand-written outputs.

- `docs/*.md` — the knowledge base; one retrieval chunk per `## ` section
- `retriever.py` — hand-rolled BM25, `TOP_K = 3` chunks per question
- `app.py` — renders `prompts/rag_answer.j2`, generates via local Ollama (`LEG_DEMO_MODEL`,
  default `qwen2.5:3b`); answers are cached in `.leg_cache/generations.json` (`core/cache.py`)

```bash
ollama pull qwen2.5:3b
poetry run python -c "from examples.demo_rag.app import DemoRAG; print(DemoRAG().answer('Can I get a refund?')[0])"
```
