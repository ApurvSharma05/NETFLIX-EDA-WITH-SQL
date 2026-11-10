"""
setup.py
--------
Automated data pipeline and database initialization for Netflix Catalog Analytics.

Capabilities:
1. Picks the dataset: --sample / $NETFLIX_CSV override, else a local full CSV, else the Kaggle
   download (kagglehub); the bundled 20-row sample is used only if the download is unavailable.
   The sample is always written to netflix_sample.db, never into netflix.db.
2. Cleans and standardizes catalog metadata (dates, countries, text trimming).
3. Ingests records into a normalized SQLite database (netflix.db).
4. Creates high-performance B-Tree indexes for fast analytical query execution.
5. Creates a compatibility view ('netflix') to ensure all analytical SQL queries work seamlessly.
"""

import os
import sys
import csv
import argparse
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
SAMPLE_DB_FILE = "netflix_sample.db"
DATASET_ID = "bhargavchirumamilla/netflix-movies-and-tv-shows-till-2025"
FULL_CSV_NAMES = [
    "netflix_movies_detailed_up_to_2025.csv",
    "netflix_titles.csv",
]
SAMPLE_CSV_NAME = "sample_netflix.csv"
SAMPLE_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAMPLE_CSV_NAME)
CSV_ENV_VAR = "NETFLIX_CSV"


def _find_csv(directory: str) -> str:
    """Returns a known catalog CSV inside `directory`, else any CSV found under it."""
    for fname in FULL_CSV_NAMES:
        candidate = os.path.join(directory, fname)
        if os.path.exists(candidate):
            return candidate
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".csv"):
                return os.path.join(root, f)
    raise FileNotFoundError(f"No CSV file found in '{directory}'")


def resolve_csv_source(use_sample: bool = False) -> str:
    """
    Picks the input CSV. Precedence:
      1. `use_sample=True` (the --sample flag) -> the bundled 20-row fixture.
      2. $NETFLIX_CSV -> that exact file.
      3. A full catalog CSV already in the working directory.
      4. The Kaggle dataset via kagglehub.
      5. Only if the download is unavailable: the bundled sample, with a warning.
    """
    if use_sample:
        logger.info(f"--sample requested: using '{SAMPLE_CSV_PATH}'")
        return SAMPLE_CSV_PATH

    override = os.environ.get(CSV_ENV_VAR)
    if override:
        if not os.path.exists(override):
            raise FileNotFoundError(f"{CSV_ENV_VAR} points to a missing file: '{override}'")
        logger.info(f"Using CSV from ${CSV_ENV_VAR}: '{override}'")
        return override

    for fname in FULL_CSV_NAMES:
        if os.path.exists(fname):
            logger.info(f"Using local dataset file: '{fname}'")
            return fname

    logger.info(f"Attempting to download '{DATASET_ID}' via kagglehub...")
    try:
        import kagglehub  # pyrefly: ignore [missing-import]
        resolved = _find_csv(kagglehub.dataset_download(DATASET_ID))
        logger.info(f"Downloaded dataset located at: '{resolved}'")
        return resolved
    except Exception as e:  # not installed, offline, no credentials, empty download
        logger.warning(f"Kaggle download unavailable ({type(e).__name__}: {e})")

    if os.path.exists(SAMPLE_CSV_PATH):
        logger.warning(
            "Falling back to the 20-row sample fixture. This is NOT the real dataset; "
            "install kagglehub / configure Kaggle credentials, or place the full CSV "
            "in the project folder, to load real data."
        )
        return SAMPLE_CSV_PATH
    raise FileNotFoundError(
        "No dataset available: Kaggle download failed and no sample CSV was found."
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


def load_data(csv_path: str, conn: sqlite3.Connection, reset: bool = False) -> int:
    """
    Reads CSV data and batch loads into SQLite.

    With reset=True the table is emptied in the same transaction as the insert, so the
    database ends up holding exactly this CSV (no leftover rows from earlier loads).
    An empty CSV never wipes the table.
    """
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
        if reset:
            c.execute("DELETE FROM netflix_titles")
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


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Netflix catalog ETL")
    parser.add_argument(
        "--sample", action="store_true",
        help=f"load the bundled 20-row fixture into '{SAMPLE_DB_FILE}' (never touches '{DB_FILE}')",
    )
    args = parser.parse_args(argv)

    logger.info("Starting Netflix Catalog ETL Pipeline...")
    try:
        csv_file = resolve_csv_source(use_sample=args.sample)
        # The sample fixture is kept out of the real database: it gets its own file.
        is_sample = os.path.basename(csv_file) == SAMPLE_CSV_NAME
        db_path = SAMPLE_DB_FILE if is_sample else DB_FILE
        conn = init_database(db_path)
        count = load_data(csv_file, conn, reset=True)
        logger.info(f"Loaded {count:,} records from '{csv_file}' into '{db_path}'")

        # Quick validation check
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM netflix_titles;")
        total_in_db = c.fetchone()[0]
        logger.info(f"Verified total records in 'netflix_titles': {total_in_db:,}")

        conn.close()
        if is_sample:
            logger.info(f"Sample DB ready. Point the API at it with NETFLIX_DB_PATH={db_path}")
        else:
            logger.info("Database ready. You can now execute 'netflix.sql' or run the FastAPI app!")
    except Exception as e:
        logger.error(f"ETL Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
