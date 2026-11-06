"""Test defaults so `pytest` runs without a .env file.

Settings are read at import time, so these must be set before any app module
is imported. The engine connects lazily: unit tests never touch this URL.
Set DATABASE_URL to a real PostgreSQL + pgvector database to run the
integration tests in tests/integration.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/contextra_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
