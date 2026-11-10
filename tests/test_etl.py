"""
tests/test_etl.py
-----------------
Unit tests for ETL transformation, cleaning, and database initialization functions.
"""

import csv
import os
import re
import sqlite3
import sys
import types

import pytest

import setup
from setup import (
    SAMPLE_CSV_PATH,
    clean_text,
    parse_release_year,
    clean_date_added,
    init_database,
    load_data,
    resolve_csv_source,
)

MINI_HEADER = "show_id,type,title,date_added,release_year\n"


def _write_csv(path, *rows):
    path.write_text(MINI_HEADER + "".join(rows), encoding="utf-8")
    return str(path)


def _fake_kagglehub(monkeypatch, download_dir=None, error=None):
    """Installs a stand-in `kagglehub` module so no network access is needed."""
    mod = types.ModuleType("kagglehub")

    def dataset_download(_dataset_id):
        if error:
            raise error
        return str(download_dir)

    mod.dataset_download = dataset_download
    monkeypatch.setitem(sys.modules, "kagglehub", mod)


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


def test_sample_csv_rows_all_parse():
    """Every sample row has exactly 12 fields and an ISO-parseable date (no column shifts)."""
    with open(SAMPLE_CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 20
    for row in rows:
        assert None not in row, f"{row['show_id']} has extra (column-shifted) fields"
        assert None not in row.values(), f"{row['show_id']} is missing fields"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean_date_added(row["date_added"])), row["show_id"]
        assert parse_release_year(row["release_year"]) is not None, row["show_id"]


def test_resolve_prefers_kaggle_over_sample(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NETFLIX_CSV", raising=False)
    dl = tmp_path / "download"
    dl.mkdir()
    (dl / "netflix_titles.csv").write_text(MINI_HEADER)
    _fake_kagglehub(monkeypatch, download_dir=dl)
    assert resolve_csv_source() == str(dl / "netflix_titles.csv")


def test_resolve_prefers_local_full_csv_over_sample(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NETFLIX_CSV", raising=False)
    (tmp_path / "netflix_titles.csv").write_text(MINI_HEADER)
    _fake_kagglehub(monkeypatch, error=AssertionError("must not download"))
    assert resolve_csv_source() == "netflix_titles.csv"


def test_resolve_falls_back_to_sample_when_download_unavailable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NETFLIX_CSV", raising=False)
    _fake_kagglehub(monkeypatch, error=RuntimeError("offline"))
    assert resolve_csv_source() == SAMPLE_CSV_PATH


def test_resolve_sample_flag_and_env_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _fake_kagglehub(monkeypatch, error=AssertionError("must not download"))
    monkeypatch.delenv("NETFLIX_CSV", raising=False)
    assert resolve_csv_source(use_sample=True) == SAMPLE_CSV_PATH

    custom = _write_csv(tmp_path / "custom.csv")
    monkeypatch.setenv("NETFLIX_CSV", custom)
    assert resolve_csv_source() == custom
    monkeypatch.setenv("NETFLIX_CSV", str(tmp_path / "missing.csv"))
    with pytest.raises(FileNotFoundError):
        resolve_csv_source()


def test_load_data_reset_replaces_existing_rows(tmp_path):
    conn = init_database(str(tmp_path / "t.db"))
    assert load_data(SAMPLE_CSV_PATH, conn) == 20
    real = _write_csv(tmp_path / "real.csv", "1,Movie,Real One,2021-01-01,2021\n")
    assert load_data(real, conn, reset=True) == 1
    ids = [r[0] for r in conn.execute("SELECT show_id FROM netflix_titles")]
    assert ids == ["1"]
    # an empty CSV must never wipe the table
    empty = _write_csv(tmp_path / "empty.csv")
    assert load_data(empty, conn, reset=True) == 0
    assert conn.execute("SELECT COUNT(*) FROM netflix_titles").fetchone()[0] == 1
    conn.close()


def test_main_sample_never_touches_real_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = init_database(setup.DB_FILE)
    real = _write_csv(tmp_path / "real.csv", "1,Movie,Real One,2021-01-01,2021\n")
    load_data(real, conn)
    conn.close()

    setup.main(["--sample"])

    real_db = sqlite3.connect(setup.DB_FILE)
    assert real_db.execute("SELECT COUNT(*) FROM netflix_titles").fetchone()[0] == 1
    real_db.close()
    sample_db = sqlite3.connect(setup.SAMPLE_DB_FILE)
    assert sample_db.execute("SELECT COUNT(*) FROM netflix_titles").fetchone()[0] == 20
    sample_db.close()


def test_main_real_load_does_not_mix_in_sample_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = init_database(setup.DB_FILE)
    load_data(SAMPLE_CSV_PATH, conn)  # simulate an old mixed/sample-polluted DB
    conn.close()

    real = _write_csv(tmp_path / "real.csv", "1,Movie,Real One,2021-01-01,2021\n",
                      "2,Movie,Real Two,2022-01-01,2022\n")
    monkeypatch.setenv("NETFLIX_CSV", real)
    setup.main([])

    db = sqlite3.connect(setup.DB_FILE)
    ids = sorted(r[0] for r in db.execute("SELECT show_id FROM netflix_titles"))
    db.close()
    assert ids == ["1", "2"]
