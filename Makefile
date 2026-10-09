.PHONY: install run test lint format

install:
	poetry install

run:
	poetry run uvicorn src.main:app --reload

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run mypy src tests

format:
	poetry run ruff check --fix .
	poetry run ruff format .
