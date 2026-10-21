"""The demo RAG app: retrieve top-k chunks, render `prompts/rag_answer.j2`, generate via Ollama.

`generate` is the `leg.config.yaml` suite `generator` hook — it turns a dataset case (just a
question) into a scored case with the app's real answer and retrieved context.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

from examples.demo_rag.retriever import BM25Retriever, load_chunks
from llm_eval_guard.core.cache import GenerationCache
from llm_eval_guard.core.models import EvalCase
from llm_eval_guard.prompts.registry import PromptRegistry

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = Path(__file__).resolve().parent / "docs"
PROMPTS_DIR = _REPO_ROOT / "prompts"

TOP_K = 3
# Why a different default from the judge: the app under test and the model grading it are
# separate roles; a small generator is also what makes the red-team findings realistic.
DEFAULT_MODEL = "qwen2.5:3b"


class DemoRAG:
    def __init__(
        self,
        *,
        top_k: int = TOP_K,
        model: str | None = None,
        base_url: str | None = None,
        cache: GenerationCache | None = None,
    ) -> None:
        self.top_k = top_k
        self.model = model or os.environ.get("LEG_DEMO_MODEL", DEFAULT_MODEL)
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.retriever = BM25Retriever(load_chunks(DOCS_DIR))
        self.prompts = PromptRegistry(PROMPTS_DIR)
        self.cache = cache

    def retrieve(self, question: str) -> list[str]:
        return self.retriever.retrieve(question, self.top_k)

    def _complete(self, prompt: str) -> str:
        if self.cache is not None and (hit := self.cache.get(self.model, prompt)) is not None:
            return hit
        resp = requests.post(
            f"{self.base_url}/api/generate",
            # temperature 0 + fixed seed: as repeatable as Ollama allows on one machine.
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0, "seed": 0},
            },
            timeout=300,
        )
        resp.raise_for_status()
        output = str(resp.json()["response"]).strip()
        if self.cache is not None:
            self.cache.set(self.model, prompt, output)
        return output

    def answer(self, question: str, context: list[str] | None = None) -> tuple[str, list[str]]:
        """Answer `question`; `context`, if given, replaces retrieval.

        Why the override: red-team cases ship their own (poisoned) documents — this simulates
        one reaching the prompt regardless of how BM25 would have ranked it.
        """
        chunks = context if context is not None else self.retrieve(question)
        prompt = self.prompts.render("rag_answer", question=question, context=chunks)
        return self._complete(prompt), chunks


_app: DemoRAG | None = None


def generate(case: EvalCase) -> EvalCase:
    """`leg` generator hook: fill `actual_output`/`retrieval_context` from the real app."""
    global _app
    if _app is None:
        _app = DemoRAG(cache=GenerationCache())
    answer, chunks = _app.answer(case.input, case.retrieval_context)
    return case.model_copy(update={"actual_output": answer, "retrieval_context": chunks})
