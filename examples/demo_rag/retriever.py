"""Hand-rolled BM25 over markdown sections — no vector store, no new dependency.

Why BM25, not embeddings: the corpus is four short docs, keyword overlap is enough to rank them,
and it keeps the demo deterministic and install-free (CLAUDE.md: no new heavy dependency).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it my of on or the to what "  # noqa: SIM905
    "when where which will with you your".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]


def load_chunks(docs_dir: Path) -> list[str]:
    """One chunk per `## ` section, prefixed with its doc and section title so a chunk is
    self-describing in the prompt (and its title words count towards ranking)."""
    chunks: list[str] = []
    for path in sorted(docs_dir.glob("*.md")):
        doc_title = ""
        for block in re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.MULTILINE):
            lines = block.strip().splitlines()
            if not lines:
                continue
            if lines[0].startswith("# "):
                doc_title = lines[0].removeprefix("# ").strip()
                continue
            body = " ".join(line.strip() for line in lines[1:] if line.strip())
            chunks.append(f"{doc_title} — {lines[0].strip()}: {body}")
    return chunks


class BM25Retriever:
    """Okapi BM25 (k1=1.5, b=0.75) over a fixed list of chunks."""

    def __init__(self, chunks: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self._k1 = k1
        self._b = b
        self._tfs = [Counter(tokenize(chunk)) for chunk in chunks]
        self._lengths = [sum(tf.values()) for tf in self._tfs]
        self._avg_len = sum(self._lengths) / len(self._lengths)
        df = Counter(term for tf in self._tfs for term in tf)
        n = len(chunks)
        self._idf = {term: math.log(1 + (n - d + 0.5) / (d + 0.5)) for term, d in df.items()}

    def _score(self, query_terms: list[str], i: int) -> float:
        tf, length = self._tfs[i], self._lengths[i]
        score = 0.0
        for term in query_terms:
            f = tf.get(term, 0)
            if f:
                norm = f + self._k1 * (1 - self._b + self._b * length / self._avg_len)
                score += self._idf[term] * f * (self._k1 + 1) / norm
        return score

    def retrieve(self, query: str, top_k: int) -> list[str]:
        terms = tokenize(query)
        ranked = sorted(range(len(self.chunks)), key=lambda i: self._score(terms, i), reverse=True)
        return [self.chunks[i] for i in ranked[:top_k]]
