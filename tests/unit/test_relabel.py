import pytest

from llm_eval_guard.core.calibration import cohen_kappa
from llm_eval_guard.core.models import EvalCase
from llm_eval_guard.core.relabel import (
    blind_sample,
    compare_labels,
    labels_from_records,
    self_agreement,
)


def _cases() -> list[EvalCase]:
    return [
        EvalCase(
            input=f"q{i}",
            actual_output=f"a{i}",
            expected_output="hint",
            retrieval_context=["ctx"],
            metadata={
                "id": f"rag-{i}",
                "failure_mode": "none",
                "note": "hint",
                "human_faithfulness": 1.0,
                "human_relevancy": 1.0 if i % 2 else 0.0,
            },
        )
        for i in range(10)
    ]


def test_blind_sample_picks_the_fraction_and_hides_label_hints() -> None:
    sample = blind_sample(_cases(), fraction=0.2, seed=1, labeler="alex")

    assert len(sample) == 2
    for record in sample:
        assert set(record) == {
            "id",
            "labeler",
            "input",
            "actual_output",
            "retrieval_context",
            "human_faithfulness",
            "human_relevancy",
        }
        assert record["human_faithfulness"] is None
        assert record["labeler"] == "alex"


def test_blind_sample_rounds_up_so_the_fraction_is_a_minimum() -> None:
    assert len(blind_sample(_cases(), fraction=0.15, seed=1, labeler="self")) == 2  # 1.5 -> 2


def test_blind_sample_is_deterministic_per_seed() -> None:
    first = blind_sample(_cases(), 0.3, seed=5, labeler="self")
    second = blind_sample(_cases(), 0.3, seed=5, labeler="alex")

    assert [r["id"] for r in first] == [r["id"] for r in second]  # same cases for every labeler


def test_self_agreement_scores_each_label_separately() -> None:
    relabeled = [
        {"id": "rag-1", "human_faithfulness": 1.0, "human_relevancy": 1.0},  # matches
        {"id": "rag-2", "human_faithfulness": 0.5, "human_relevancy": 1.0},  # relevancy flips
    ]

    faithfulness, relevancy = self_agreement(_cases(), relabeled)

    assert faithfulness.pass_fail_agreement == 1.0  # 0.5 still counts as pass
    assert faithfulness.exact_agreement == 0.5
    assert faithfulness.mean_absolute_error == pytest.approx(0.25)
    assert relevancy.pass_fail_agreement == 0.5
    assert relevancy.n == 2


def test_self_agreement_rejects_unfilled_labels() -> None:
    relabeled = [{"id": "rag-1", "human_faithfulness": 1.0, "human_relevancy": None}]

    with pytest.raises(ValueError, match="not filled in"):
        self_agreement(_cases(), relabeled)


def test_self_agreement_rejects_unknown_ids() -> None:
    with pytest.raises(ValueError, match="unknown case id"):
        self_agreement(
            _cases(), [{"id": "nope", "human_faithfulness": 1.0, "human_relevancy": 1.0}]
        )


def test_self_agreement_lists_the_cases_that_differ() -> None:
    relabeled = [
        {"id": "rag-1", "human_faithfulness": 1.0, "human_relevancy": 1.0},
        {"id": "rag-2", "human_faithfulness": 0.5, "human_relevancy": 1.0},
    ]

    faithfulness, relevancy = self_agreement(_cases(), relabeled)

    assert faithfulness.disagreements == ["rag-2"]
    assert relevancy.disagreements == ["rag-2"]


def test_labels_from_records_rejects_duplicate_ids() -> None:
    record = {"id": "rag-1", "human_faithfulness": 1.0, "human_relevancy": 1.0}

    with pytest.raises(ValueError, match="duplicate"):
        labels_from_records([record, record])


def _labels(passes: list[bool]) -> dict[str, dict[str, float]]:
    return {
        f"rag-{i}": {"human_faithfulness": 1.0 if p else 0.0, "human_relevancy": 1.0}
        for i, p in enumerate(passes)
    }


def test_cohen_kappa_matches_a_hand_computed_example() -> None:
    # 10 items, raters agree on 8: p_o = 0.8. Both pass 6/10, so
    # p_e = 0.6*0.6 + 0.4*0.4 = 0.52 and kappa = (0.8 - 0.52) / (1 - 0.52) = 7/12.
    a = [True] * 6 + [False] * 4
    b = [True] * 5 + [False] * 4 + [True]

    assert cohen_kappa(a, b) == pytest.approx(7 / 12)


def test_cohen_kappa_is_zero_at_chance_and_undefined_when_constant() -> None:
    assert cohen_kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert cohen_kappa([True, False], [True, False]) == 1.0
    assert cohen_kappa([True, True], [True, True]) is None
    assert cohen_kappa([], []) is None


def test_cohen_kappa_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="differ"):
        cohen_kappa([True], [True, False])


def test_compare_labels_reports_kappa_between_two_labelers() -> None:
    a = _labels([True] * 6 + [False] * 4)
    b = _labels([True] * 5 + [False] * 4 + [True])

    faithfulness, relevancy = compare_labels(a, b)

    assert faithfulness.pass_fail_agreement == pytest.approx(0.8)
    assert faithfulness.pass_fail_kappa == pytest.approx(7 / 12)
    assert faithfulness.disagreements == ["rag-5", "rag-9"]
    assert relevancy.pass_fail_kappa is None  # both labelers pass everything


def test_compare_labels_rejects_an_empty_label_set() -> None:
    with pytest.raises(ValueError, match="no labeled records"):
        compare_labels(_labels([True]), {})
