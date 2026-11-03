.PHONY: install run test lint fix-lint format typecheck

install:
	poetry install

run:
	poetry run uvicorn src.main:app --reload

test:
	poetry run pytest

lint:
	poetry run ruff check .

fix-lint:
	poetry run ruff check --fix .

format:
	poetry run ruff format .

typecheck:
	poetry run mypy src
