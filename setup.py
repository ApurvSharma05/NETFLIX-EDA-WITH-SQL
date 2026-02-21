"""
setup_database.py
-----------------
Loads the Kaggle Netflix dataset into a local SQLite database using kagglehub.

Steps:
    1. Install kagglehub: pip install kagglehub
    2. Run: python setup_database.py
    3. Then open netflix_analysis.sql in any SQLite client to run queries.
"""

import sqlite3
import csv
import os
import kagglehub

DB_FILE = "netflix.db"
DATASET_ID = "bhargavchirumamilla/netflix-movies-and-tv-shows-till-2025"
CSV_FILENAME = "netflix_movies_detailed_up_to_2025.csv"

# Download dataset
print("📥 Downloading dataset from Kaggle...")
path = kagglehub.dataset_download(DATASET_ID)
csv_file = os.path.join(path, CSV_FILENAME)

if not os.path.exists(csv_file):
    raise FileNotFoundError(f"'{CSV_FILENAME}' not found in downloaded dataset.")

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

c.execute("DROP TABLE IF EXISTS netflix_titles")
c.execute("""
    CREATE TABLE netflix_titles (
        show_id      TEXT PRIMARY KEY,
        type         TEXT,
        title        TEXT,
        director     TEXT,
        cast         TEXT,
        country      TEXT,
        date_added   TEXT,
        release_year INTEGER,
        rating       TEXT,
        duration     TEXT,
        listed_in    TEXT,
        description  TEXT
    )
""")

with open(csv_file, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = [
        (
            row["show_id"],
            row["type"],
            row["title"],
            row.get("director", ""),
            row.get("cast", ""),
            row.get("country", ""),
            row.get("date_added", ""),
            int(row["release_year"]) if row.get("release_year") else None,
            row.get("rating", ""),
            row.get("duration", ""),
            row.get("listed_in", ""),
            row.get("description", ""),
        )
        for row in reader
    ]

c.executemany(
    "INSERT OR IGNORE INTO netflix_titles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
    rows
)
conn.commit()
print(f"✅ Loaded {len(rows):,} records into '{DB_FILE}'")
conn.close()