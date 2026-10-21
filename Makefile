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
	poetry run coverage run -m pytest
	poetry run coverage report

run:
	poetry run leg run
