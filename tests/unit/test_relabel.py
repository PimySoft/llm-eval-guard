import pytest

from llm_eval_guard.core.models import EvalCase
from llm_eval_guard.core.relabel import blind_sample, self_agreement


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
    sample = blind_sample(_cases(), fraction=0.2, seed=1)

    assert len(sample) == 2
    for record in sample:
        assert set(record) == {
            "id",
            "input",
            "actual_output",
            "retrieval_context",
            "human_faithfulness",
            "human_relevancy",
        }
        assert record["human_faithfulness"] is None


def test_blind_sample_is_deterministic_per_seed() -> None:
    assert blind_sample(_cases(), 0.3, seed=5) == blind_sample(_cases(), 0.3, seed=5)


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
        self_agreement(_cases(), [{"id": "nope", "human_faithfulness": 1.0}])
