"""
src/schemas.py
--------------
Pydantic schemas for request validation and structured API responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    database_file: str = Field(..., examples=["netflix.db"])
    total_records: int = Field(..., examples=[16000])


class CatalogMetricsResponse(BaseModel):
    total_titles: int = Field(..., description="Total titles in the catalog")
    movies_count: int = Field(..., description="Count of Movie titles")
    tv_shows_count: int = Field(..., description="Count of TV Show titles")
    unique_countries: int = Field(..., description="Count of distinct countries represented")
    earliest_release_year: Optional[int] = Field(None, description="Earliest release year")
    latest_release_year: Optional[int] = Field(None, description="Most recent release year")


class ContentSplitItem(BaseModel):
    type: str = Field(..., examples=["Movie"])
    total_content: int = Field(..., examples=[16000])


class DominantRatingItem(BaseModel):
    type: str = Field(..., examples=["Movie"])
    rating: str = Field(..., examples=["TV-MA"])
    count: Optional[int] = None


class CountryDistributionItem(BaseModel):
    country: str = Field(..., examples=["United States"])
    total_content: int = Field(..., examples=[5421])


class IndiaTrendItem(BaseModel):
    country: str = Field(..., examples=["India"])
    release_year: int = Field(..., examples=[2021])
    total_release: int = Field(..., examples=[63])
    avg_release_pct: float = Field(..., examples=[15.04])


class TitleItem(BaseModel):
    show_id: str
    type: str
    title: str
    director: Optional[str] = None
    casts: Optional[str] = None
    country: Optional[str] = None
    date_added: Optional[str] = None
    release_year: Optional[int] = None
    rating: Optional[str] = None
    duration: Optional[str] = None
    listed_in: Optional[str] = None
    description: Optional[str] = None
    content_label: Optional[str] = Field(None, description="'Standard' or 'Flagged' based on content description")


class TitlesListResponse(BaseModel):
    total_matches: int
    limit: int
    offset: int
    items: List[TitleItem]
