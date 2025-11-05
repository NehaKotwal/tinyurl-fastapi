"""
Database seeding script.
Adds sample data for testing.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.url import URLCreate
from src.repository.url_repository import DatabaseConnection, URLRepository
from src.services.url_service import URLService
from src.services.encoder import ShortCodeGenerator
from src.utils.exceptions import CustomAliasAlreadyExistsException
from src.config import settings


def seed_database():
    """Seed database with sample data."""
    print("Seeding database with sample data...")

    # Initialize components
    db_connection = DatabaseConnection(settings.database_url)
    repository = URLRepository(db_connection)
    generator = ShortCodeGenerator(min_length=settings.short_code_length)
    service = URLService(repository=repository, short_code_generator=generator)

    # Sample URLs
    sample_urls = [
        {
            "original_url": "https://www.github.com",
            "custom_alias": "github",
        },
        {
            "original_url": "https://www.google.com",
            "custom_alias": "google",
        },
        {
            "original_url": "https://www.stackoverflow.com",
            "custom_alias": "stackoverflow",
        },
        {
            "original_url": "https://www.medium.com/article/very-long-url-path",
            "custom_alias": "medium",
        },
        {
            "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "custom_alias": "video",
        },
        {
            "original_url": "https://www.wikipedia.org",
            "custom_alias": "wiki",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30)
        },
    ]

    created_count = 0
    skipped_count = 0

    for url_data in sample_urls:
        try:
            url_create = URLCreate(**url_data)
            result = service.shorten_url(url_create)
            print(f"✓ Created: {result.short_url} -> {result.original_url}")
            created_count += 1
        except CustomAliasAlreadyExistsException as e:
            alias = url_data.get('custom_alias', 'N/A')
            print(f"⊘ Skipped: '{alias}' already exists")
            skipped_count += 1
        except Exception as e:
            print(f"✗ Failed to create URL: {str(e)}")

    print(f"\n{'='*60}")
    print(f"Seeding complete!")
    print(f"  Created: {created_count} URLs")
    print(f"  Skipped: {skipped_count} URLs (already exist)")
    print(f"  Total:   {created_count + skipped_count} URLs")
    print(f"{'='*60}")


if __name__ == "__main__":
    seed_database()
