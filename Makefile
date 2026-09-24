.PHONY: lint format typecheck test install run

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

run:
	poetry run leg run
