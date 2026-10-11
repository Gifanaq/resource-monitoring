.PHONY: install run test

install:
	poetry install

run:
	poetry run uvicorn src.main:app --reload

test:
	poetry run pytest
