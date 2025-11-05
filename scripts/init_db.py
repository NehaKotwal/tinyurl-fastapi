"""
Database initialization script.
Creates tables and sets up the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.url import Base
from src.repository.url_repository import DatabaseConnection
from src.config import settings


def init_database():
    """Initialize database with tables."""
    print(f"Initializing database at: {settings.database_url}")

    # Create database connection
    db_connection = DatabaseConnection(settings.database_url)

    # Create all tables
    Base.metadata.create_all(bind=db_connection.engine)

    print("Database initialized successfully!")
    print("Tables created:")
    for table in Base.metadata.tables.keys():
        print(f"  - {table}")


if __name__ == "__main__":
    init_database()
