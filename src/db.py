"""
src/db.py
---------
Database connection lifecycle, session management, and compatibility views.
"""

import os
import sqlite3
from typing import Generator

DB_PATH = os.getenv("NETFLIX_DB_PATH", "netflix.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Creates a configured connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Ensure compatibility view and indexes exist
    c = conn.cursor()
    c.execute("""
        CREATE VIEW IF NOT EXISTS netflix AS
        SELECT
            show_id,
            type,
            title,
            director,
            [cast] AS casts,
            country,
            date_added,
            release_year,
            rating,
            duration,
            listed_in,
            description
        FROM netflix_titles;
    """)
    conn.commit()
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for yielding database connections."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
