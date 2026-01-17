.PHONY: lint lint-fix test test-integration test-e2e test-all run buildx

lint:
	uv run ruff check .
	uv run ruff format --check .

lint-fix:
	uv run ruff check . --fix
	uv run ruff format .

test:
	uv run pytest tests --cache-clear -v --ignore=tests/e2e --ignore=tests/integration

test-integration:
	uv run pytest tests/integration -v --tb=short

test-e2e:
	uv run pytest tests/e2e -v --tb=short

test-all:
	$(MAKE) test
	$(MAKE) test-integration
	$(MAKE) test-e2e

run:
	uv run fastapi dev src/api/main.py

buildx:
	docker buildx build --platform linux/amd64 -t wbe7/teeshka-core:dev .
