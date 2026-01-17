# tests/integration/__init__.py
"""Integration tests package marker.

Integration tests require external services (Redis, Postgres, etc.)
to be running. These are excluded from unit tests but included in
'make test-all' or 'make test-integration'.
"""
