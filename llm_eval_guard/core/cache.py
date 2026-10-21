"""Disk-backed caches: judge-scored ``MetricResult``s (``ResultCache``) and system-under-test
generations (``GenerationCache``).

``ResultCache`` is keyed on ``(metric, scope, input, output, context)`` — ``scope`` carries the
judge model and threshold, so switching either re-scores.

Why: the local Ollama judge is $0 but not free of *time* — re-scoring an unchanged golden/red-team
case on every CI re-run (plan.md Phase 5.4) burns CI minutes on a result that can't have changed.
This is scoped to non-``fast`` (judge) metrics only — schema/rule-based checks are already
instant, so caching them would add bookkeeping for no measurable speedup.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from llm_eval_guard.core.models import EvalCase, MetricResult

DEFAULT_CACHE_PATH = Path(".leg_cache/judge_results.json")
DEFAULT_GENERATION_CACHE_PATH = Path(".leg_cache/generations.json")


def _cache_key(metric_name: str, case: EvalCase, scope: str) -> str:
    payload = json.dumps(
        {
            "metric": metric_name,
            "scope": scope,
            "input": case.input,
            "actual_output": case.actual_output,
            "expected_output": case.expected_output,
            "retrieval_context": case.retrieval_context,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResultCache:
    """A flat JSON dict on disk: cache key -> serialized ``MetricResult``.

    Why JSON on disk instead of e.g. sqlite/diskcache: the cache is small (one entry per
    metric/case pair in the golden + red-team datasets), read/written at most once per `leg run`
    invocation, and a plain file is what `actions/cache` (see .github/workflows/ci.yml) can
    restore/save without extra tooling.
    """

    def __init__(self, path: Path = DEFAULT_CACHE_PATH) -> None:
        self._path = path
        self._data: dict[str, dict[str, object]] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def get(self, metric_name: str, case: EvalCase, scope: str = "") -> MetricResult | None:
        raw = self._data.get(_cache_key(metric_name, case, scope))
        return MetricResult.model_validate(raw) if raw is not None else None

    def set(self, metric_name: str, case: EvalCase, result: MetricResult, scope: str = "") -> None:
        self._data[_cache_key(metric_name, case, scope)] = result.model_dump()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")


class GenerationCache:
    """A flat JSON dict on disk: ``(model, prompt)`` hash -> generated text, for a suite's
    ``generator`` (e.g. ``examples/demo_rag``) to skip re-generating an unchanged answer.

    Why key on the fully rendered prompt: it already contains the template and the retrieved
    chunks, so a prompt edit or a retriever change (the Phase 9 regression demo) is a cache miss
    by construction — no invalidation rules to forget. Writes through on every ``set`` so an
    interrupted run keeps what it already generated.
    """

    def __init__(self, path: Path = DEFAULT_GENERATION_CACHE_PATH) -> None:
        self._path = path
        self._data: dict[str, str] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _key(model: str, prompt: str) -> str:
        payload = json.dumps({"model": model, "prompt": prompt}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, model: str, prompt: str) -> str | None:
        return self._data.get(self._key(model, prompt))

    def set(self, model: str, prompt: str, output: str) -> None:
        self._data[self._key(model, prompt)] = output
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
