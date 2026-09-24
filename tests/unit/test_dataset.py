from pathlib import Path

import pytest

from llm_eval_guard.core.dataset import load_golden_dataset

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


def test_sample_rag_qa_dataset_loads_and_has_human_labels() -> None:
    cases = load_golden_dataset(SAMPLE_DATASET)

    assert len(cases) >= 10
    for case in cases:
        assert "human_faithfulness" in case.metadata
        assert "human_relevancy" in case.metadata
        assert 0.0 <= case.metadata["human_faithfulness"] <= 1.0
        assert 0.0 <= case.metadata["human_relevancy"] <= 1.0
