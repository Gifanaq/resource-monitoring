.PHONY: install run test lint format up down dev logs

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

up:
	docker compose up -d --build

down:
	docker compose down

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

logs:
	docker compose logs -f
