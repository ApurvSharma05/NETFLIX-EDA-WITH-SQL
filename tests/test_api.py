"""
tests/test_api.py
-----------------
Functional test suite for FastAPI REST endpoints.
"""

from fastapi import status


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_records"] > 0


def test_catalog_metrics(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_titles"] > 0
    assert data["movies_count"] > 0
    assert data["tv_shows_count"] > 0


def test_content_split(client):
    response = client.get("/api/v1/analytics/content-split")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 2
    types = [item["type"] for item in data]
    assert "Movie" in types
    assert "TV Show" in types


def test_dominant_ratings(client):
    response = client.get("/api/v1/analytics/dominant-ratings")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 2


def test_top_countries(client):
    response = client.get("/api/v1/analytics/top-countries?limit=3")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) <= 3
    assert len(data) > 0


def test_india_trends(client):
    response = client.get("/api/v1/analytics/india-trends?limit=5")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)


def test_list_titles_filtering_and_pagination(client):
    # Test filtering by type = Movie
    response = client.get("/api/v1/titles?type=Movie&limit=5")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) <= 5
    for item in data["items"]:
        assert item["type"] == "Movie"

    # Test filtering by actor = 'Salman Khan'
    response_actor = client.get("/api/v1/titles?actor=Salman%20Khan")
    assert response_actor.status_code == status.HTTP_200_OK
    data_actor = response_actor.json()
    assert data_actor["total_matches"] >= 2

    # Test filtering by classification = 'Flagged'
    response_flagged = client.get("/api/v1/titles?classification=Flagged")
    assert response_flagged.status_code == status.HTTP_200_OK
    data_flagged = response_flagged.json()
    for item in data_flagged["items"]:
        assert item["content_label"] == "Flagged"


def test_get_title_by_id(client):
    # Success case
    response = client.get("/api/v1/titles/s1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["show_id"] == "s1"
    assert data["title"] == "Dick Johnson Is Dead"

    # 404 Not Found case
    response_404 = client.get("/api/v1/titles/nonexistent_id")
    assert response_404.status_code == status.HTTP_404_NOT_FOUND
