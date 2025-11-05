"""
Unit tests for URL repository.
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.repository.url_repository import URLRepository, DatabaseConnection
from src.models.url import Base
from src.utils.exceptions import (
    URLNotFoundException,
    CustomAliasAlreadyExistsException,
    DatabaseException
)


@pytest.fixture
def db_connection():
    """Create in-memory database connection for testing."""
    connection = DatabaseConnection("sqlite:///:memory:")
    Base.metadata.create_all(bind=connection.engine)
    yield connection
    Base.metadata.drop_all(bind=connection.engine)


@pytest.fixture
def repository(db_connection):
    """Create repository instance with test database."""
    return URLRepository(db_connection)


class TestURLRepository:
    """Test URL repository operations."""

    def test_create_url(self, repository):
        """Test creating a URL entry."""
        url_entry = repository.create(
            original_url="https://www.example.com",
            custom_alias=None,
            expires_at=None,
            user_id=None
        )

        assert url_entry.id is not None
        assert url_entry.original_url == "https://www.example.com"
        assert url_entry.click_count == 0

    def test_create_url_with_custom_alias(self, repository):
        """Test creating URL with custom alias."""
        url_entry = repository.create(
            original_url="https://www.example.com",
            custom_alias="mylink",
            expires_at=None,
            user_id=None
        )

        assert url_entry.custom_alias == "mylink"

    def test_create_duplicate_custom_alias(self, repository):
        """Test that duplicate custom alias raises exception."""
        repository.create(
            original_url="https://www.example.com",
            custom_alias="duplicate"
        )

        with pytest.raises(CustomAliasAlreadyExistsException):
            repository.create(
                original_url="https://www.example2.com",
                custom_alias="duplicate"
            )

    def test_update_short_code(self, repository):
        """Test updating short code."""
        url_entry = repository.create(
            original_url="https://www.example.com"
        )

        updated_entry = repository.update_short_code(url_entry.id, "abc123")
        assert updated_entry.short_code == "abc123"

    def test_update_short_code_not_found(self, repository):
        """Test updating short code for non-existent entry."""
        with pytest.raises(URLNotFoundException):
            repository.update_short_code(99999, "abc123")

    def test_get_by_short_code(self, repository):
        """Test getting URL by short code."""
        url_entry = repository.create(
            original_url="https://www.example.com"
        )
        repository.update_short_code(url_entry.id, "abc123")

        found_entry = repository.get_by_short_code("abc123")
        assert found_entry is not None
        assert found_entry.short_code == "abc123"

    def test_get_by_short_code_not_found(self, repository):
        """Test getting non-existent short code."""
        result = repository.get_by_short_code("nonexistent")
        assert result is None

    def test_get_by_custom_alias(self, repository):
        """Test getting URL by custom alias."""
        repository.create(
            original_url="https://www.example.com",
            custom_alias="mylink"
        )

        found_entry = repository.get_by_custom_alias("mylink")
        assert found_entry is not None
        assert found_entry.custom_alias == "mylink"

    def test_get_by_id(self, repository):
        """Test getting URL by ID."""
        url_entry = repository.create(
            original_url="https://www.example.com"
        )

        found_entry = repository.get_by_id(url_entry.id)
        assert found_entry is not None
        assert found_entry.id == url_entry.id

    def test_update_url(self, repository):
        """Test updating URL."""
        url_entry = repository.create(
            original_url="https://www.example.com"
        )
        repository.update_short_code(url_entry.id, "abc123")

        updated_entry = repository.update(
            short_code="abc123",
            original_url="https://www.newurl.com"
        )

        assert updated_entry.original_url == "https://www.newurl.com"

    def test_update_url_not_found(self, repository):
        """Test updating non-existent URL."""
        with pytest.raises(URLNotFoundException):
            repository.update(
                short_code="nonexistent",
                original_url="https://www.example.com"
            )

    def test_delete_url(self, repository):
        """Test deleting URL."""
        url_entry = repository.create(
            original_url="https://www.example.com"
        )
        repository.update_short_code(url_entry.id, "abc123")

        result = repository.delete("abc123")
        assert result is True

        # Verify deletion
        found_entry = repository.get_by_short_code("abc123")
        assert found_entry is None

    def test_delete_url_not_found(self, repository):
        """Test deleting non-existent URL."""
        result = repository.delete("nonexistent")
        assert result is False

    def test_increment_click_count(self, repository):
        """Test incrementing click count."""
        url_entry = repository.create(
            original_url="https://www.example.com"
        )
        repository.update_short_code(url_entry.id, "abc123")

        initial_count = url_entry.click_count

        updated_entry = repository.increment_click_count("abc123")
        assert updated_entry.click_count == initial_count + 1
        assert updated_entry.last_accessed_at is not None

    def test_increment_click_count_not_found(self, repository):
        """Test incrementing click count for non-existent URL."""
        with pytest.raises(URLNotFoundException):
            repository.increment_click_count("nonexistent")

    def test_list_all_urls(self, repository):
        """Test listing all URLs."""
        # Create multiple URLs
        for i in range(5):
            repository.create(original_url=f"https://www.example{i}.com")

        urls = repository.list_all(limit=10, offset=0)
        assert len(urls) == 5

    def test_list_all_urls_with_pagination(self, repository):
        """Test listing URLs with pagination."""
        # Create multiple URLs
        for i in range(10):
            repository.create(original_url=f"https://www.example{i}.com")

        # Test limit
        urls = repository.list_all(limit=5, offset=0)
        assert len(urls) == 5

        # Test offset
        urls = repository.list_all(limit=5, offset=5)
        assert len(urls) == 5

    def test_list_all_urls_with_user_filter(self, repository):
        """Test listing URLs filtered by user ID."""
        # Create URLs for different users
        repository.create(original_url="https://www.example1.com", user_id="user1")
        repository.create(original_url="https://www.example2.com", user_id="user1")
        repository.create(original_url="https://www.example3.com", user_id="user2")

        # Filter by user1
        urls = repository.list_all(user_id="user1")
        assert len(urls) == 2

    def test_count_all_urls(self, repository):
        """Test counting all URLs."""
        # Create multiple URLs
        for i in range(7):
            repository.create(original_url=f"https://www.example{i}.com")

        count = repository.count_all()
        assert count == 7

    def test_count_all_urls_with_user_filter(self, repository):
        """Test counting URLs filtered by user ID."""
        # Create URLs for different users
        repository.create(original_url="https://www.example1.com", user_id="user1")
        repository.create(original_url="https://www.example2.com", user_id="user1")
        repository.create(original_url="https://www.example3.com", user_id="user2")

        count = repository.count_all(user_id="user1")
        assert count == 2

    def test_create_url_with_expiration(self, repository):
        """Test creating URL with expiration date."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        url_entry = repository.create(
            original_url="https://www.example.com",
            expires_at=expires_at
        )

        assert url_entry.expires_at is not None
        assert url_entry.expires_at.date() == expires_at.date()
