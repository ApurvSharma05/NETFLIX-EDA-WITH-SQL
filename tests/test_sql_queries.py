"""
tests/test_sql_queries.py
-------------------------
Regression test suite ensuring all analytical SQL queries execute without errors
and return expected statistical outputs.
"""

import sqlite3
import pytest


def test_q1_movie_vs_tv_shows_split(test_conn):
    cursor = test_conn.cursor()
    cursor.execute("SELECT type, COUNT(*) AS total FROM netflix GROUP BY type ORDER BY total DESC;")
    results = dict(cursor.fetchall())
    assert "Movie" in results
    assert "TV Show" in results
    assert results["Movie"] > 0
    assert results["TV Show"] > 0


def test_q2_dominant_rating_window_function(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT type, rating
        FROM (
            SELECT
                type,
                rating,
                COUNT(*) AS count,
                RANK() OVER (PARTITION BY type ORDER BY COUNT(*) DESC) AS ranking
            FROM netflix
            WHERE rating IS NOT NULL AND rating != ''
            GROUP BY type, rating
        ) AS ranked
        WHERE ranking = 1;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    assert len(rows) >= 2  # At least one for Movie, one for TV Show
    types_found = {r["type"] for r in rows}
    assert "Movie" in types_found
    assert "TV Show" in types_found


def test_q3_release_year_2020(test_conn):
    cursor = test_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM netflix WHERE type = 'Movie' AND release_year = 2020;")
    count = cursor.fetchone()[0]
    assert count >= 1


def test_q4_top_countries_json_unnesting(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT
            TRIM(value) AS country,
            COUNT(show_id) AS total_content
        FROM netflix,
             json_each('["' || REPLACE(country, ', ', '","') || '"]')
        WHERE country IS NOT NULL AND country != ''
        GROUP BY country
        ORDER BY total_content DESC
        LIMIT 5;
    """
    cursor.execute(query)
    results = cursor.fetchall()
    assert len(results) > 0
    top_country = results[0]["country"]
    assert len(top_country) > 0


def test_q5_longest_movie(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT
            title,
            CAST(REPLACE(duration, ' min', '') AS INTEGER) AS runtime_min
        FROM netflix
        WHERE type = 'Movie' AND duration LIKE '%min%'
        ORDER BY runtime_min DESC
        LIMIT 1;
    """
    cursor.execute(query)
    longest = cursor.fetchone()
    assert longest is not None
    assert longest["runtime_min"] > 60


def test_q6_resilient_date_filter(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT COUNT(*)
        FROM netflix
        WHERE (
            CASE
                WHEN date_added LIKE '____-__-__%' THEN CAST(SUBSTR(TRIM(date_added), 1, 4) AS INTEGER)
                ELSE CAST(SUBSTR(TRIM(date_added), -4) AS INTEGER)
            END
        ) >= (CAST(STRFTIME('%Y', 'now') AS INTEGER) - 10);
    """
    cursor.execute(query)
    count = cursor.fetchone()[0]
    assert count > 0


def test_q7_director_search(test_conn):
    cursor = test_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM netflix WHERE director LIKE '%Rajiv Chilaka%';")
    count = cursor.fetchone()[0]
    assert count == 1


def test_q8_tv_shows_seasons_threshold(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT COUNT(*)
        FROM netflix
        WHERE type = 'TV Show'
          AND CAST(
              TRIM(REPLACE(REPLACE(duration, ' Seasons', ''), ' Season', ''))
              AS INTEGER
          ) > 5;
    """
    cursor.execute(query)
    count = cursor.fetchone()[0]
    assert count >= 1  # e.g., Friends (10 seasons), Great British Baking Show (9 seasons)


def test_q10_india_trend_percentage(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT
            country,
            release_year,
            COUNT(show_id) AS total_release,
            ROUND(
                COUNT(show_id) * 1.0 /
                (SELECT COUNT(show_id) FROM netflix WHERE country LIKE '%India%') * 100,
                2
            ) AS avg_release_pct
        FROM netflix
        WHERE country LIKE '%India%'
        GROUP BY country, release_year
        ORDER BY avg_release_pct DESC
        LIMIT 5;
    """
    cursor.execute(query)
    results = cursor.fetchall()
    assert len(results) > 0


def test_q15_content_moderation_labels(test_conn):
    cursor = test_conn.cursor()
    query = """
        SELECT
            category,
            COUNT(*) AS content_count
        FROM (
            SELECT
                CASE
                    WHEN description LIKE '%kill%' OR description LIKE '%violence%' THEN 'Bad'
                    ELSE 'Good'
                END AS category
            FROM netflix
        ) AS categorized
        GROUP BY category
        ORDER BY content_count DESC;
    """
    cursor.execute(query)
    counts = dict(cursor.fetchall())
    assert "Bad" in counts
    assert "Good" in counts
    assert counts["Good"] > counts["Bad"]


def test_bonus_queries(test_conn):
    cursor = test_conn.cursor()

    # B1: additions by year
    cursor.execute("""
        SELECT
            CASE
                WHEN date_added LIKE '____-__-__%' THEN SUBSTR(TRIM(date_added), 1, 4)
                ELSE SUBSTR(TRIM(date_added), -4)
            END AS year_added,
            COUNT(*) AS titles_added
        FROM netflix
        WHERE date_added IS NOT NULL AND date_added != ''
        GROUP BY year_added ORDER BY year_added DESC;
    """)
    assert len(cursor.fetchall()) > 0

    # B4: US vs International
    cursor.execute("""
        SELECT
            CASE WHEN country LIKE '%United States%' THEN 'US Content' ELSE 'International' END AS origin,
            COUNT(*) AS total
        FROM netflix
        WHERE country IS NOT NULL AND country != ''
        GROUP BY origin;
    """)
    origins = dict(cursor.fetchall())
    assert "US Content" in origins
    assert "International" in origins
