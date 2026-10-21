from collections import Counter
from pathlib import Path

import pytest

from llm_eval_guard.core.dataset import load_dataset_cases, load_golden_dataset
from llm_eval_guard.core.models import EvalCase

SAMPLE_DATASET = Path(__file__).parent.parent.parent / "datasets" / "golden" / "sample_rag_qa.jsonl"


def test_load_golden_dataset_parses_all_fields(tmp_path) -> None:
    dataset_file = tmp_path / "cases.jsonl"
    dataset_file.write_text(
        '{"input": "q1", "actual_output": "a1", "expected_output": "e1", '
        '"retrieval_context": ["ctx1"], "metadata": {"category": "easy"}}\n'
        '{"input": "q2", "actual_output": "a2"}\n',
        encoding="utf-8",
    )

    cases = load_golden_dataset(dataset_file)

    assert len(cases) == 2
    assert cases[0].input == "q1"
    assert cases[0].retrieval_context == ["ctx1"]
    assert cases[0].metadata == {"category": "easy"}
    assert cases[1].expected_output is None
    assert cases[1].metadata == {}


def test_load_golden_dataset_skips_blank_lines(tmp_path) -> None:
    dataset_file = tmp_path / "cases.jsonl"
    dataset_file.write_text(
        '{"input": "q1", "actual_output": "a1"}\n\n   \n{"input": "q2", "actual_output": "a2"}\n',
        encoding="utf-8",
    )

    cases = load_golden_dataset(dataset_file)

    assert len(cases) == 2


def test_load_golden_dataset_raises_clear_error_on_malformed_json(tmp_path) -> None:
    dataset_file = tmp_path / "cases.jsonl"
    dataset_file.write_text('{"input": "q1", "actual_output": "a1"}\nnot json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="cases.jsonl:2"):
        load_golden_dataset(dataset_file)


def test_load_dataset_cases_accepts_a_single_path(tmp_path) -> None:
    dataset_file = tmp_path / "cases.jsonl"
    dataset_file.write_text('{"input": "q1", "actual_output": "a1"}\n', encoding="utf-8")

    cases = load_dataset_cases(dataset_file)

    assert len(cases) == 1


def test_load_dataset_cases_concatenates_multiple_paths_in_order(tmp_path) -> None:
    first = tmp_path / "first.jsonl"
    first.write_text('{"input": "q1", "actual_output": "a1"}\n', encoding="utf-8")
    second = tmp_path / "second.jsonl"
    second.write_text('{"input": "q2", "actual_output": "a2"}\n', encoding="utf-8")

    cases = load_dataset_cases([first, second])

    assert [c.input for c in cases] == ["q1", "q2"]


CATEGORIES = {"single-fact", "multi-hop", "context-missing", "verbose", "ambiguous"}
# A failure mode implies which label must fail — see docs/datasets.md.
FAITHFULNESS_FAILURES = {
    "hallucinated-detail",
    "contradiction",
    "unsupported-claim",
    "partially-grounded",
}
RELEVANCY_FAILURES = {"off-topic", "unhelpful-refusal"}
FAILURE_MODES = {"none"} | FAITHFULNESS_FAILURES | RELEVANCY_FAILURES


def _should_fail(case: EvalCase) -> bool:
    return bool(min(case.metadata["human_faithfulness"], case.metadata["human_relevancy"]) < 0.5)


def test_sample_rag_qa_dataset_loads_and_has_human_labels() -> None:
    cases = load_golden_dataset(SAMPLE_DATASET)

    assert len(cases) >= 50
    for case in cases:
        assert "human_faithfulness" in case.metadata
        assert "human_relevancy" in case.metadata
        assert 0.0 <= case.metadata["human_faithfulness"] <= 1.0
        assert 0.0 <= case.metadata["human_relevancy"] <= 1.0


def test_sample_rag_qa_metadata_fields_are_valid() -> None:
    cases = load_golden_dataset(SAMPLE_DATASET)

    ids = [c.metadata["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    for case in cases:
        assert case.metadata["category"] in CATEGORIES, case.metadata["id"]
        assert case.metadata["failure_mode"] in FAILURE_MODES, case.metadata["id"]
        assert case.metadata["split"] in {"dev", "test"}, case.metadata["id"]
        assert case.retrieval_context, case.metadata["id"]


def test_sample_rag_qa_failure_mode_matches_labels() -> None:
    for case in load_golden_dataset(SAMPLE_DATASET):
        mode = case.metadata["failure_mode"]
        faithful = case.metadata["human_faithfulness"] >= 0.5
        relevant = case.metadata["human_relevancy"] >= 0.5
        expected = (mode not in FAITHFULNESS_FAILURES, mode not in RELEVANCY_FAILURES)
        assert (faithful, relevant) == expected, f"{case.metadata['id']} ({mode})"


def test_sample_rag_qa_is_balanced_between_pass_and_fail() -> None:
    cases = load_golden_dataset(SAMPLE_DATASET)

    fail_rate = sum(_should_fail(c) for c in cases) / len(cases)

    assert 0.4 <= fail_rate <= 0.6


def test_sample_rag_qa_split_is_roughly_70_30_and_covers_every_failure_mode() -> None:
    cases = load_golden_dataset(SAMPLE_DATASET)

    test_share = sum(c.metadata["split"] == "test" for c in cases) / len(cases)
    modes_by_split = Counter((c.metadata["split"], c.metadata["failure_mode"]) for c in cases)

    assert 0.25 <= test_share <= 0.35
    for mode in FAILURE_MODES:
        assert modes_by_split["dev", mode] >= 1, f"{mode} missing from dev"
        assert modes_by_split["test", mode] >= 1, f"{mode} missing from test"
