"""
Integration tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from src.main import create_app
from src.repository.url_repository import DatabaseConnection
from src.models.url import Base


@pytest.fixture
def test_db():
    """Create test database."""
    db_connection = DatabaseConnection("sqlite:///:memory:")
    Base.metadata.create_all(bind=db_connection.engine)
    yield db_connection
    Base.metadata.drop_all(bind=db_connection.engine)


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data


class TestShortenEndpoint:
    """Test URL shortening endpoint."""

    def test_shorten_url_success(self, client):
        """Test successful URL shortening."""
        payload = {
            "original_url": "https://www.example.com"
        }
        response = client.post("/api/shorten", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["original_url"] == "https://www.example.com"
        assert len(data["short_code"]) >= 6

    def test_shorten_url_with_custom_alias(self, client):
        """Test URL shortening with custom alias."""
        import uuid
        unique_alias = f"mylink-{uuid.uuid4().hex[:8]}"
        payload = {
            "original_url": "https://www.example.com",
            "custom_alias": unique_alias
        }
        response = client.post("/api/shorten", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["custom_alias"] == unique_alias

    def test_shorten_url_duplicate_alias(self, client):
        """Test that duplicate custom alias is rejected."""
        import uuid
        unique_alias = f"dup-{uuid.uuid4().hex[:8]}"
        payload = {
            "original_url": "https://www.example.com",
            "custom_alias": unique_alias
        }

        # First request should succeed
        response1 = client.post("/api/shorten", json=payload)
        assert response1.status_code == 201

        # Second request with same alias should fail
        response2 = client.post("/api/shorten", json=payload)
        assert response2.status_code == 409

    def test_shorten_url_without_scheme(self, client):
        """Test shortening URL without scheme."""
        payload = {
            "original_url": "www.example.com"
        }
        response = client.post("/api/shorten", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["original_url"].startswith("https://")

    def test_shorten_url_invalid(self, client):
        """Test shortening invalid URL."""
        payload = {
            "original_url": "not a valid url"
        }
        response = client.post("/api/shorten", json=payload)
        assert response.status_code == 400

    def test_shorten_url_with_expiration(self, client):
        """Test shortening URL with expiration date."""
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        payload = {
            "original_url": "https://www.example.com",
            "expires_at": expires_at
        }
        response = client.post("/api/shorten", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["expires_at"] is not None


class TestRedirectEndpoint:
    """Test URL redirection endpoint."""

    def test_redirect_success(self, client):
        """Test successful redirection."""
        # Create shortened URL
        payload = {"original_url": "https://www.example.com"}
        create_response = client.post("/api/shorten", json=payload)
        short_code = create_response.json()["short_code"]

        # Test redirect
        redirect_response = client.get(f"/{short_code}", follow_redirects=False)
        assert redirect_response.status_code == 307
        assert "location" in redirect_response.headers
        assert redirect_response.headers["location"] == "https://www.example.com"

    def test_redirect_with_custom_alias(self, client):
        """Test redirection using custom alias."""
        import uuid
        unique_alias = f"test-{uuid.uuid4().hex[:8]}"
        # Create shortened URL with custom alias
        payload = {
            "original_url": "https://www.example.com",
            "custom_alias": unique_alias
        }
        create_response = client.post("/api/shorten", json=payload)
        assert create_response.status_code == 201
        data = create_response.json()
        assert data["custom_alias"] == unique_alias

        # Test redirect using custom alias
        redirect_response = client.get(f"/{unique_alias}", follow_redirects=False)
        assert redirect_response.status_code == 307
        assert "location" in redirect_response.headers
        assert redirect_response.headers["location"] == "https://www.example.com"

    def test_redirect_not_found(self, client):
        """Test redirection for non-existent short code."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_redirect_increments_counter(self, client):
        """Test that redirection increments click counter."""
        # Create shortened URL
        payload = {"original_url": "https://www.example.com"}
        create_response = client.post("/api/shorten", json=payload)
        short_code = create_response.json()["short_code"]

        # Get initial stats
        stats_response = client.get(f"/api/urls/{short_code}/stats")
        initial_count = stats_response.json()["click_count"]

        # Perform redirect
        client.get(f"/{short_code}", follow_redirects=False)

        # Check updated stats
        stats_response = client.get(f"/api/urls/{short_code}/stats")
        new_count = stats_response.json()["click_count"]

        assert new_count == initial_count + 1


class TestListURLsEndpoint:
    """Test listing URLs endpoint."""

    def test_list_urls_empty(self, client):
        """Test listing when no URLs exist."""
        response = client.get("/api/urls")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_urls_with_data(self, client):
        """Test listing URLs with existing data."""
        # Create some URLs
        for i in range(3):
            payload = {"original_url": f"https://www.example{i}.com"}
            client.post("/api/shorten", json=payload)

        # List URLs
        response = client.get("/api/urls")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    def test_list_urls_pagination(self, client):
        """Test listing URLs with pagination."""
        # Create URLs
        for i in range(5):
            payload = {"original_url": f"https://www.example{i}.com"}
            client.post("/api/shorten", json=payload)

        # Test limit
        response = client.get("/api/urls?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test offset
        response = client.get("/api/urls?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


class TestStatsEndpoint:
    """Test statistics endpoints."""

    def test_get_url_stats(self, client):
        """Test getting statistics for a URL."""
        # Create URL
        payload = {"original_url": "https://www.example.com"}
        create_response = client.post("/api/shorten", json=payload)
        short_code = create_response.json()["short_code"]

        # Get stats
        response = client.get(f"/api/urls/{short_code}/stats")
        assert response.status_code == 200

        data = response.json()
        assert "short_code" in data
        assert "click_count" in data
        assert "created_at" in data
        assert data["click_count"] == 0

    def test_get_url_stats_not_found(self, client):
        """Test getting stats for non-existent URL."""
        response = client.get("/api/urls/nonexistent/stats")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Summary stats endpoint removed in simplified API")
    def test_get_summary_stats(self, client):
        """Test getting summary statistics."""
        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total_urls" in data
        assert "base_url" in data


@pytest.mark.skip(reason="UPDATE endpoint removed in simplified API")
class TestUpdateEndpoint:
    """Test URL update endpoint."""

    def test_update_url_destination(self, client):
        """Test updating URL destination."""
        # Create URL
        payload = {"original_url": "https://www.example.com"}
        create_response = client.post("/api/shorten", json=payload)
        short_code = create_response.json()["short_code"]

        # Update URL
        update_payload = {"original_url": "https://www.newdestination.com"}
        response = client.put(f"/api/urls/{short_code}", json=update_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["original_url"] == "https://www.newdestination.com"

    def test_update_url_not_found(self, client):
        """Test updating non-existent URL."""
        update_payload = {"original_url": "https://www.example.com"}
        response = client.put("/api/urls/nonexistent", json=update_payload)
        assert response.status_code == 404


@pytest.mark.skip(reason="DELETE endpoint removed in simplified API")
class TestDeleteEndpoint:
    """Test URL deletion endpoint."""

    def test_delete_url_success(self, client):
        """Test successful URL deletion."""
        # Create URL
        payload = {"original_url": "https://www.example.com"}
        create_response = client.post("/api/shorten", json=payload)
        short_code = create_response.json()["short_code"]

        # Delete URL
        response = client.delete(f"/api/urls/{short_code}")
        assert response.status_code == 204

        # Verify deletion
        get_response = client.get(f"/{short_code}")
        assert get_response.status_code == 404

    def test_delete_url_not_found(self, client):
        """Test deleting non-existent URL."""
        response = client.delete("/api/urls/nonexistent")
        assert response.status_code == 404
