.PHONY: lint lint-fix test run buildx

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

buildx:
	docker buildx build --platform linux/amd64 -t wbe7/teeshka-core:dev .
