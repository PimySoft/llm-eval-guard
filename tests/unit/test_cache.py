from pathlib import Path

from llm_eval_guard.core.cache import GenerationCache, ResultCache
from llm_eval_guard.core.models import EvalCase, MetricResult


def _case(actual_output: str = "x") -> EvalCase:
    return EvalCase(input="q", actual_output=actual_output)


def test_miss_then_hit_round_trips(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path / "cache.json")
    case = _case()

    assert cache.get("faithfulness", case) is None

    result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason="ok")
    cache.set("faithfulness", case, result)

    assert cache.get("faithfulness", case) == result


def test_different_case_is_a_separate_key(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path / "cache.json")
    result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason=None)
    cache.set("faithfulness", _case("x"), result)

    assert cache.get("faithfulness", _case("y")) is None


def test_different_metric_is_a_separate_key(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path / "cache.json")
    result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason=None)
    cache.set("faithfulness", _case(), result)

    assert cache.get("answer_relevancy", _case()) is None


def test_save_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "cache.json"
    cache = ResultCache(path)
    result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason=None)
    cache.set("faithfulness", _case(), result)
    cache.save()

    assert path.exists()
    reloaded = ResultCache(path)
    assert reloaded.get("faithfulness", _case()) == result


def test_different_scope_is_a_separate_key(tmp_path: Path) -> None:
    """A score cached under one judge model/threshold must not be served for another."""
    cache = ResultCache(tmp_path / "cache.json")
    result = MetricResult(metric_name="faithfulness", score=0.9, passed=True, reason=None)
    cache.set("faithfulness", _case(), result, scope="qwen2.5:0.5b@0.8")

    assert cache.get("faithfulness", _case(), scope="qwen2.5:7b@0.6") is None
    assert cache.get("faithfulness", _case(), scope="qwen2.5:0.5b@0.8") == result


def test_generation_cache_round_trips_and_writes_through(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "gen.json"
    GenerationCache(path).set("model", "prompt", "answer")

    reloaded = GenerationCache(path)
    assert reloaded.get("model", "prompt") == "answer"
    assert reloaded.get("other-model", "prompt") is None
    assert reloaded.get("model", "other prompt") is None
