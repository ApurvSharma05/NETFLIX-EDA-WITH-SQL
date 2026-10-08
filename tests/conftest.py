"""
tests/conftest.py
-----------------
Pytest fixtures providing in-memory database and FastAPI test client.
"""

import os
import sys
import sqlite3
import pytest
from starlette.testclient import TestClient

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from setup import init_database, load_data
from src.api import app
from src.db import get_db

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "sample_netflix.csv")


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Initializes a temporary test SQLite database populated with sample data."""
    tmp_dir = tmp_path_factory.mktemp("db_test")
    db_file = os.path.join(tmp_dir, "test_netflix.db")

    conn = init_database(db_file)
    load_data(SAMPLE_CSV, conn)
    conn.close()

    return db_file


@pytest.fixture
def test_conn(test_db_path):
    """Provides a connection to the populated test database."""
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def client(test_db_path):
    """Provides a TestClient with overridden get_db dependency pointing to test database."""
    def override_get_db():
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
