"""The Phase 9 demo app (examples/demo_rag/) with Ollama stubbed — no network call."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from examples.demo_rag import app as demo_app
from examples.demo_rag.app import DemoRAG
from examples.demo_rag.retriever import BM25Retriever, load_chunks, tokenize
from llm_eval_guard.core.cache import GenerationCache
from llm_eval_guard.core.models import EvalCase


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self._text = text

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"response": self._text}


@pytest.fixture
def ollama_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, json: dict[str, Any], timeout: int) -> _FakeResponse:
        calls.append({"url": url, **json})
        return _FakeResponse(" stub answer ")

    monkeypatch.setattr("examples.demo_rag.app.requests.post", fake_post)
    return calls


def test_tokenize_drops_stopwords_and_punctuation() -> None:
    assert tokenize("What is the Pro plan's price?") == ["pro", "plan", "s", "price"]


def test_load_chunks_makes_one_titled_chunk_per_section() -> None:
    chunks = load_chunks(demo_app.DOCS_DIR)

    assert len(chunks) == 16
    assert chunks[0].startswith("Billing — Payment methods: ")


def test_bm25_ranks_the_matching_chunk_first() -> None:
    retriever = BM25Retriever(["apples are red", "bananas are yellow", "cherries are red too"])

    assert retriever.retrieve("yellow bananas", top_k=1) == ["bananas are yellow"]
    assert len(retriever.retrieve("red", top_k=2)) == 2


def test_answer_renders_the_rag_prompt_with_retrieved_chunks(ollama_calls) -> None:
    rag = DemoRAG(model="m", base_url="http://ollama")

    answer, chunks = rag.answer("How much storage does the Pro plan include?")

    assert answer == "stub answer"
    assert len(chunks) == demo_app.TOP_K
    assert any("2TB" in c for c in chunks)
    (call,) = ollama_calls
    assert call["url"] == "http://ollama/api/generate"
    assert call["model"] == "m"
    assert "using only the context below" in call["prompt"]
    assert chunks[0] in call["prompt"]


def test_answer_uses_provided_context_instead_of_retrieving(ollama_calls) -> None:
    _, chunks = DemoRAG().answer("Summarize this.", context=["poisoned doc"])

    assert chunks == ["poisoned doc"]
    assert "- poisoned doc" in ollama_calls[0]["prompt"]


def test_generation_cache_skips_the_second_call(ollama_calls, tmp_path: Path) -> None:
    cache = GenerationCache(tmp_path / "gen.json")
    DemoRAG(cache=cache).answer("Where is my data stored?")
    DemoRAG(cache=GenerationCache(tmp_path / "gen.json")).answer("Where is my data stored?")

    assert len(ollama_calls) == 1


def test_a_retriever_change_is_a_cache_miss(ollama_calls, tmp_path: Path) -> None:
    cache = GenerationCache(tmp_path / "gen.json")
    DemoRAG(cache=cache, top_k=3).answer("Where is my data stored?")
    DemoRAG(cache=cache, top_k=1).answer("Where is my data stored?")

    assert len(ollama_calls) == 2


def test_generate_hook_fills_output_and_context(ollama_calls, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(demo_app, "_app", DemoRAG(cache=GenerationCache(tmp_path / "g.json")))

    case = demo_app.generate(EvalCase(input="Can I get a refund?", actual_output=""))

    assert case.actual_output == "stub answer"
    assert case.retrieval_context is not None
    assert len(case.retrieval_context) == demo_app.TOP_K
