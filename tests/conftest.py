from pathlib import Path

import pytest

from llm_eval_guard.core import EvalCase, load_golden_dataset

# Lets tests/unit/test_pytest_plugin.py spin up an inner pytest run via the `pytester` fixture to
# exercise our plugin's marker/hook behavior end-to-end (the pytest-recommended way to test a
# pytest plugin, rather than hand-faking a FixtureRequest).
pytest_plugins = ["pytester"]

GOLDEN_DATASET_PATH = Path(__file__).parent.parent / "datasets" / "golden" / "sample_rag_qa.jsonl"


@pytest.fixture(scope="session")
def golden_dataset() -> list[EvalCase]:
    """The hand-labeled RAG QA cases in datasets/golden/sample_rag_qa.jsonl.

    See docs/datasets.md for the schema.
    """
    return load_golden_dataset(GOLDEN_DATASET_PATH)
