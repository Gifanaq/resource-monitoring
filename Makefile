.PHONY: install run test

install:
	poetry install

run:
	poetry run uvicorn tpumon.main:app --reload

test:
	poetry run pytest
