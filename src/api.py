"""
src/api.py
----------
FastAPI application serving Netflix catalog analytics, metrics, and search.
"""

import sqlite3
from typing import List, Optional
from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.db import get_db, DB_PATH
from src.schemas import (
    HealthResponse,
    CatalogMetricsResponse,
    ContentSplitItem,
    DominantRatingItem,
    CountryDistributionItem,
    IndiaTrendItem,
    TitlesListResponse,
    TitleItem,
)

app = FastAPI(
    title="Netflix Catalog Intelligence API",
    description=(
        "Production-ready REST API providing catalog analytics, window-function insights, "
        "and content filtering over the Netflix SQL catalog database."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check and database verification",
)
def health_check(db: sqlite3.Connection = Depends(get_db)):
    """Verifies that the API service is active and the database is accessible."""
    try:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM netflix;")
        total = cursor.fetchone()[0]
        return HealthResponse(
            status="healthy",
            database_file=DB_PATH,
            total_records=total,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable or uninitialized: {e}",
        )


@app.get(
    "/api/v1/metrics",
    response_model=CatalogMetricsResponse,
    tags=["Analytics"],
    summary="High-level catalog metrics summary",
)
def get_catalog_metrics(db: sqlite3.Connection = Depends(get_db)):
    """Computes high-level catalog volume, breakdown, and year ranges."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) AS total_titles,
            SUM(CASE WHEN type = 'Movie' THEN 1 ELSE 0 END) AS movies_count,
            SUM(CASE WHEN type = 'TV Show' THEN 1 ELSE 0 END) AS tv_shows_count,
            COUNT(DISTINCT country) AS unique_countries,
            MIN(release_year) AS earliest_year,
            MAX(release_year) AS latest_year
        FROM netflix;
    """)
    row = cursor.fetchone()
    return CatalogMetricsResponse(
        total_titles=row["total_titles"] or 0,
        movies_count=row["movies_count"] or 0,
        tv_shows_count=row["tv_shows_count"] or 0,
        unique_countries=row["unique_countries"] or 0,
        earliest_release_year=row["earliest_year"],
        latest_release_year=row["latest_year"],
    )


@app.get(
    "/api/v1/analytics/content-split",
    response_model=List[ContentSplitItem],
    tags=["Analytics"],
    summary="Q1: Count Movies vs TV Shows",
)
def get_content_split(db: sqlite3.Connection = Depends(get_db)):
    """Returns the volume breakdown between Movies and TV Shows."""
    cursor = db.cursor()
    cursor.execute("SELECT type, COUNT(*) AS total_content FROM netflix GROUP BY type ORDER BY total_content DESC;")
    return [ContentSplitItem(**dict(r)) for r in cursor.fetchall()]


@app.get(
    "/api/v1/analytics/dominant-ratings",
    response_model=List[DominantRatingItem],
    tags=["Analytics"],
    summary="Q2: Most common rating per content type via window functions",
)
def get_dominant_ratings(db: sqlite3.Connection = Depends(get_db)):
    """Calculates the mode rating per type using RANK() OVER window function."""
    cursor = db.cursor()
    query = """
        SELECT type, rating, count
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
    return [DominantRatingItem(**dict(r)) for r in cursor.fetchall()]


@app.get(
    "/api/v1/analytics/top-countries",
    response_model=List[CountryDistributionItem],
    tags=["Analytics"],
    summary="Q4: Top producing countries with unnested geographic representation",
)
def get_top_countries(
    limit: int = Query(5, ge=1, le=50, description="Number of top countries to return"),
    db: sqlite3.Connection = Depends(get_db)
):
    """Unnests comma-delimited country values using JSON virtual table unnesting."""
    cursor = db.cursor()
    query = """
        SELECT
            TRIM(value) AS country,
            COUNT(show_id) AS total_content
        FROM netflix,
             json_each('["' || REPLACE(country, ', ', '","') || '"]')
        WHERE country IS NOT NULL AND country != ''
        GROUP BY country
        ORDER BY total_content DESC
        LIMIT :limit;
    """
    cursor.execute(query, {"limit": limit})
    return [CountryDistributionItem(**dict(r)) for r in cursor.fetchall()]


@app.get(
    "/api/v1/analytics/india-trends",
    response_model=List[IndiaTrendItem],
    tags=["Analytics"],
    summary="Q10: Top release years and percentage contribution for India",
)
def get_india_trends(
    limit: int = Query(5, ge=1, le=20),
    db: sqlite3.Connection = Depends(get_db)
):
    """Calculates percentage of Indian content released per year."""
    cursor = db.cursor()
    query = """
        SELECT
            country,
            release_year,
            COUNT(show_id) AS total_release,
            ROUND(
                COUNT(show_id) * 1.0 /
                (SELECT COUNT(show_id) FROM netflix WHERE country = 'India' OR country LIKE '%India%') * 100,
                2
            ) AS avg_release_pct
        FROM netflix
        WHERE country = 'India' OR country LIKE '%India%'
        GROUP BY country, release_year
        ORDER BY avg_release_pct DESC
        LIMIT :limit;
    """
    cursor.execute(query, {"limit": limit})
    return [IndiaTrendItem(**dict(r)) for r in cursor.fetchall()]


@app.get(
    "/api/v1/titles",
    response_model=TitlesListResponse,
    tags=["Catalog Titles"],
    summary="Search, filter, and paginate catalog titles",
)
def list_titles(
    type: Optional[str] = Query(None, description="Filter by 'Movie' or 'TV Show'"),
    country: Optional[str] = Query(None, description="Filter by country substring"),
    actor: Optional[str] = Query(None, description="Filter by actor name in cast"),
    director: Optional[str] = Query(None, description="Filter by director name"),
    release_year: Optional[int] = Query(None, description="Filter by specific release year"),
    classification: Optional[str] = Query(None, description="'Standard' or 'Flagged' (Q15 content moderation)"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db)
):
    """Provides advanced catalog querying with dynamic filters and pagination."""
    cursor = db.cursor()

    conditions = ["1=1"]
    params = {}

    if type:
        conditions.append("type = :type")
        params["type"] = type
    if country:
        conditions.append("country LIKE :country")
        params["country"] = f"%{country}%"
    if actor:
        conditions.append("casts LIKE :actor")
        params["actor"] = f"%{actor}%"
    if director:
        conditions.append("director LIKE :director")
        params["director"] = f"%{director}%"
    if release_year:
        conditions.append("release_year = :release_year")
        params["release_year"] = release_year
    if search:
        conditions.append("(title LIKE :search OR description LIKE :search)")
        params["search"] = f"%{search}%"
    if classification:
        if classification.lower() == "flagged":
            conditions.append("(description LIKE '%kill%' OR description LIKE '%violence%')")
        elif classification.lower() == "standard":
            conditions.append("(description NOT LIKE '%kill%' AND description NOT LIKE '%violence%')")

    where_clause = " AND ".join(conditions)

    # Count total matching rows
    count_query = f"SELECT COUNT(*) FROM netflix WHERE {where_clause};"
    cursor.execute(count_query, params)
    total_matches = cursor.fetchone()[0]

    # Fetch paginated items with Q15 classification label
    select_query = f"""
        SELECT
            show_id,
            type,
            title,
            director,
            casts,
            country,
            date_added,
            release_year,
            rating,
            duration,
            listed_in,
            description,
            CASE
                WHEN description LIKE '%kill%' OR description LIKE '%violence%' THEN 'Flagged'
                ELSE 'Standard'
            END AS content_label
        FROM netflix
        WHERE {where_clause}
        ORDER BY release_year DESC, title ASC
        LIMIT :limit OFFSET :offset;
    """
    params["limit"] = limit
    params["offset"] = offset

    cursor.execute(select_query, params)
    items = [TitleItem(**dict(r)) for r in cursor.fetchall()]

    return TitlesListResponse(
        total_matches=total_matches,
        limit=limit,
        offset=offset,
        items=items,
    )


@app.get(
    "/api/v1/titles/{show_id}",
    response_model=TitleItem,
    tags=["Catalog Titles"],
    summary="Get single title by show_id",
)
def get_title_by_id(show_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Retrieves full metadata for an individual title."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT
            show_id, type, title, director, casts, country,
            date_added, release_year, rating, duration, listed_in, description,
            CASE
                WHEN description LIKE '%kill%' OR description LIKE '%violence%' THEN 'Flagged'
                ELSE 'Standard'
            END AS content_label
        FROM netflix
        WHERE show_id = :show_id;
    """, {"show_id": show_id})
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Title with show_id '{show_id}' not found.",
        )
    return TitleItem(**dict(row))
