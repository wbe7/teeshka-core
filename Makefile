.PHONY: lint lint-fix test run

lint:
	uv run ruff check .
	uv run ruff format --check .

lint-fix:
	uv run ruff check . --fix
	uv run ruff format .

test:
	uv run pytest --cache-clear -v

run:
	uv run fastapi dev src/api/main.py
