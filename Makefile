.PHONY: lint format typecheck test cov install run

install:
	poetry install --extras deepeval

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

typecheck:
	poetry run mypy

test:
	poetry run pytest

cov:
	poetry run pytest --cov=llm_eval_guard --cov-report=term-missing

run:
	poetry run leg run
