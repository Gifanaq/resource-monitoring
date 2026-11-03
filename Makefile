.PHONY: install run test lint fix-lint format typecheck prod down dev logs

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

prod:
	docker compose up -d --build

down:
	docker compose down

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

logs:
	docker compose logs -f
