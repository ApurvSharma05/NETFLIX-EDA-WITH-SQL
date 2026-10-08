"""
tests/test_etl.py
-----------------
Unit tests for ETL transformation, cleaning, and database initialization functions.
"""

import sqlite3
import pytest
from setup import clean_text, parse_release_year, clean_date_added, init_database


def test_clean_text():
    assert clean_text("  hello world  ") == "hello world"
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_parse_release_year():
    assert parse_release_year("2021") == 2021
    assert parse_release_year(" 2020.0 ") == 2020
    assert parse_release_year(None) is None
    assert parse_release_year("invalid_year") is None


def test_clean_date_added():
    assert clean_date_added("September 25, 2021") == "2021-09-25"
    assert clean_date_added("2021-09-25") == "2021-09-25"
    assert clean_date_added(None) == ""


def test_database_initialization(tmp_path):
    test_db = str(tmp_path / "test_init.db")
    conn = init_database(test_db)
    cursor = conn.cursor()

    # Verify table existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='netflix_titles';")
    assert cursor.fetchone() is not None

    # Verify view existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='netflix';")
    assert cursor.fetchone() is not None

    # Verify index existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_titles_release_year';")
    assert cursor.fetchone() is not None

    conn.close()
