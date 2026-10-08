"""
setup.py
--------
Automated data pipeline and database initialization for Netflix Catalog Analytics.

Capabilities:
1. Downloads dataset via kagglehub (or gracefully falls back to local CSV if present).
2. Cleans and standardizes catalog metadata (dates, countries, text trimming).
3. Ingests records into a normalized SQLite database (netflix.db).
4. Creates high-performance B-Tree indexes for fast analytical query execution.
5. Creates a compatibility view ('netflix') to ensure all analytical SQL queries work seamlessly.
"""

import os
import sys
import csv
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("netflix_etl")

DB_FILE = "netflix.db"
DATASET_ID = "bhargavchirumamilla/netflix-movies-and-tv-shows-till-2025"
CANDIDATE_CSV_NAMES = [
    "netflix_movies_detailed_up_to_2025.csv",
    "netflix_titles.csv",
    "sample_netflix.csv"
]


def resolve_csv_source() -> str:
    """Finds a local CSV or downloads the dataset via kagglehub."""
    # Check if a candidate CSV already exists in the workspace
    for fname in CANDIDATE_CSV_NAMES:
        if os.path.exists(fname):
            logger.info(f"Using local dataset file: '{fname}'")
            return fname

    # Attempt download via kagglehub
    logger.info(f"Attempting to download '{DATASET_ID}' via kagglehub...")
    try:
        import kagglehub
        path = kagglehub.dataset_download(DATASET_ID)
        for fname in CANDIDATE_CSV_NAMES:
            candidate = os.path.join(path, fname)
            if os.path.exists(candidate):
                logger.info(f"Downloaded dataset located at: '{candidate}'")
                return candidate
        
        # If specific filename not found, search for any CSV in download directory
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".csv"):
                    resolved = os.path.join(root, f)
                    logger.info(f"Found CSV in downloaded archive: '{resolved}'")
                    return resolved
        raise FileNotFoundError(f"No CSV file found in Kaggle download path '{path}'")
    except ImportError:
        logger.warning("'kagglehub' package is not installed. To install: pip install kagglehub")
        raise FileNotFoundError(
            "Dataset CSV not found locally. Please place 'netflix_titles.csv' or "
            "'netflix_movies_detailed_up_to_2025.csv' in the project folder, or install kagglehub."
        )


def clean_text(val: Optional[str]) -> str:
    """Safely cleans and strips text strings."""
    return val.strip() if val else ""


def parse_release_year(val: Optional[str]) -> Optional[int]:
    """Safely extracts release year as an integer."""
    if not val:
        return None
    try:
        return int(float(val.strip()))
    except (ValueError, TypeError):
        return None


def clean_date_added(val: Optional[str]) -> str:
    """Standardizes dates to ISO YYYY-MM-DD when possible."""
    if not val:
        return ""
    val = val.strip()
    # Check if already ISO format
    if len(val) == 10 and val[4] == '-' and val[7] == '-':
        return val
    # Try parsing text format e.g. 'September 25, 2021'
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d-%b-%y"):
        try:
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return val


def init_database(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Initializes the database schema, indexes, and compatibility view."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create canonical table
    c.execute("""
        CREATE TABLE IF NOT EXISTS netflix_titles (
            show_id      TEXT PRIMARY KEY,
            type         TEXT NOT NULL,
            title        TEXT NOT NULL,
            director     TEXT,
            cast         TEXT,
            country      TEXT,
            date_added   TEXT,
            release_year INTEGER,
            rating       TEXT,
            duration     TEXT,
            listed_in    TEXT,
            description  TEXT
        );
    """)

    # Create indexes for optimal analytical query performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_titles_type ON netflix_titles(type);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_titles_release_year ON netflix_titles(release_year);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_titles_country ON netflix_titles(country);")

    # Create compatibility view
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


def load_data(csv_path: str, conn: sqlite3.Connection) -> int:
    """Reads CSV data and batch loads into SQLite."""
    c = conn.cursor()
    rows_to_insert: List[Tuple] = []

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle possible variations in column naming
            show_id = clean_text(row.get("show_id") or row.get("id"))
            if not show_id:
                continue

            content_type = clean_text(row.get("type") or "Movie")
            title = clean_text(row.get("title") or "Untitled")
            director = clean_text(row.get("director"))
            cast_members = clean_text(row.get("cast") or row.get("casts"))
            country = clean_text(row.get("country"))
            date_added = clean_date_added(row.get("date_added"))
            release_year = parse_release_year(row.get("release_year"))
            rating = clean_text(row.get("rating"))
            duration = clean_text(row.get("duration"))
            listed_in = clean_text(row.get("listed_in") or row.get("genres"))
            description = clean_text(row.get("description") or row.get("overview"))

            rows_to_insert.append((
                show_id,
                content_type,
                title,
                director,
                cast_members,
                country,
                date_added,
                release_year,
                rating,
                duration,
                listed_in,
                description
            ))

    if rows_to_insert:
        c.executemany(
            """
            INSERT OR REPLACE INTO netflix_titles (
                show_id, type, title, director, cast, country,
                date_added, release_year, rating, duration, listed_in, description
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows_to_insert
        )
        conn.commit()

    return len(rows_to_insert)


def main():
    logger.info("🎬 Starting Netflix Catalog ETL Pipeline...")
    try:
        csv_file = resolve_csv_source()
        conn = init_database(DB_FILE)
        count = load_data(csv_file, conn)
        logger.info(f"✅ Successfully processed and loaded {count:,} records into '{DB_FILE}'")

        # Quick validation check
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM netflix_titles;")
        total_in_db = c.fetchone()[0]
        logger.info(f"📊 Verified total records in 'netflix_titles': {total_in_db:,}")

        conn.close()
        logger.info("🚀 Database ready. You can now execute 'netflix.sql' or run the FastAPI app!")
    except Exception as e:
        logger.error(f"❌ ETL Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()