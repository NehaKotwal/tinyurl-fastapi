"""
Repository pattern for URL database operations.
Abstracts database operations and provides a clean interface.
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from contextlib import contextmanager

from src.models.url import URLModel, Base
from src.utils.exceptions import (
    DatabaseException,
    URLNotFoundException,
    CustomAliasAlreadyExistsException
)


class DatabaseConnection:
    """
    Database connection manager using Singleton pattern.
    Ensures only one database connection pool exists.
    """

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls, database_url: str = None):
        """Singleton pattern implementation."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, database_url: str = None):
        """
        Initialize database connection.

        Args:
            database_url: SQLAlchemy database URL
        """
        if database_url and not self._engine:
            self._engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
                pool_pre_ping=True,
                echo=False
            )
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
            Base.metadata.create_all(bind=self._engine)

    @property
    def engine(self):
        """Get database engine."""
        return self._engine

    @property
    def session_factory(self):
        """Get session factory."""
        return self._session_factory

    @contextmanager
    def get_session(self):
        """
        Get database session with automatic cleanup.

        Yields:
            Database session
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class URLRepository:
    """
    Repository for URL database operations.
    Implements Repository pattern to abstract database logic.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize repository.

        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection

    def create(self, original_url: str, custom_alias: Optional[str] = None,
               expires_at: Optional[datetime] = None, user_id: Optional[str] = None) -> URLModel:
        """
        Create a new URL entry.

        Args:
            original_url: Original long URL
            custom_alias: Optional custom alias
            expires_at: Optional expiration datetime
            user_id: Optional user identifier

        Returns:
            Created URLModel

        Raises:
            CustomAliasAlreadyExistsException: If custom alias already exists
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                # Check if custom alias exists
                if custom_alias:
                    existing = session.query(URLModel).filter(
                        URLModel.custom_alias == custom_alias
                    ).first()
                    if existing:
                        raise CustomAliasAlreadyExistsException(
                            f"Custom alias '{custom_alias}' already exists"
                        )

                # Create URL entry without short_code (will be set later)
                url_entry = URLModel(
                    short_code=None,  # Temporary, will be updated after getting ID
                    original_url=original_url,
                    custom_alias=custom_alias,
                    expires_at=expires_at,
                    user_id=user_id,
                    created_at=datetime.now(timezone.utc),
                    click_count=0
                )

                session.add(url_entry)
                session.flush()  # Get the ID without committing
                session.refresh(url_entry)
                session.expunge(url_entry)  # Detach from session so it can be used outside

                return url_entry

        except CustomAliasAlreadyExistsException:
            raise
        except IntegrityError as e:
            raise CustomAliasAlreadyExistsException("Duplicate entry") from e
        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def update_short_code(self, url_id: int, short_code: str) -> URLModel:
        """
        Update short code for a URL entry.

        Args:
            url_id: URL entry ID
            short_code: Generated short code

        Returns:
            Updated URLModel

        Raises:
            URLNotFoundException: If URL not found
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                url_entry = session.query(URLModel).filter(URLModel.id == url_id).first()
                if not url_entry:
                    raise URLNotFoundException(f"URL with ID {url_id} not found")

                url_entry.short_code = short_code
                session.add(url_entry)
                session.flush()
                session.refresh(url_entry)
                session.expunge(url_entry)  # Detach from session

                return url_entry

        except URLNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def get_by_short_code(self, short_code: str) -> Optional[URLModel]:
        """
        Get URL entry by short code.

        Args:
            short_code: Short code to lookup

        Returns:
            URLModel or None if not found
        """
        try:
            with self.db_connection.get_session() as session:
                result = session.query(URLModel).filter(
                    URLModel.short_code == short_code
                ).first()
                if result:
                    session.expunge(result)
                return result

        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def get_by_custom_alias(self, custom_alias: str) -> Optional[URLModel]:
        """
        Get URL entry by custom alias.

        Args:
            custom_alias: Custom alias to lookup

        Returns:
            URLModel or None if not found
        """
        try:
            with self.db_connection.get_session() as session:
                result = session.query(URLModel).filter(
                    URLModel.custom_alias == custom_alias
                ).first()
                if result:
                    session.expunge(result)
                return result

        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def get_by_id(self, url_id: int) -> Optional[URLModel]:
        """
        Get URL entry by ID.

        Args:
            url_id: URL entry ID

        Returns:
            URLModel or None if not found
        """
        try:
            with self.db_connection.get_session() as session:
                result = session.query(URLModel).filter(URLModel.id == url_id).first()
                if result:
                    session.expunge(result)
                return result

        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def update(self, short_code: str, original_url: Optional[str] = None,
               expires_at: Optional[datetime] = None) -> URLModel:
        """
        Update URL entry.

        Args:
            short_code: Short code of URL to update
            original_url: New original URL (optional)
            expires_at: New expiration datetime (optional)

        Returns:
            Updated URLModel

        Raises:
            URLNotFoundException: If URL not found
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                url_entry = session.query(URLModel).filter(
                    URLModel.short_code == short_code
                ).first()

                if not url_entry:
                    raise URLNotFoundException(f"URL with short code '{short_code}' not found")

                if original_url:
                    url_entry.original_url = original_url
                if expires_at is not None:
                    url_entry.expires_at = expires_at

                session.add(url_entry)
                session.flush()
                session.refresh(url_entry)
                session.expunge(url_entry)  # Detach from session

                return url_entry

        except URLNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def delete(self, short_code: str) -> bool:
        """
        Delete URL entry.

        Args:
            short_code: Short code of URL to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                url_entry = session.query(URLModel).filter(
                    URLModel.short_code == short_code
                ).first()

                if not url_entry:
                    return False

                session.delete(url_entry)
                return True

        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def increment_click_count(self, short_code: str) -> URLModel:
        """
        Increment click count and update last accessed time.

        Args:
            short_code: Short code or custom alias

        Returns:
            Updated URLModel

        Raises:
            URLNotFoundException: If URL not found
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                # Try to find by short_code first
                url_entry = session.query(URLModel).filter(
                    URLModel.short_code == short_code
                ).first()

                # If not found, try custom_alias
                if not url_entry:
                    url_entry = session.query(URLModel).filter(
                        URLModel.custom_alias == short_code
                    ).first()

                if not url_entry:
                    raise URLNotFoundException(f"URL with short code or alias '{short_code}' not found")

                url_entry.click_count += 1
                url_entry.last_accessed_at = datetime.now(timezone.utc)

                session.add(url_entry)
                session.flush()
                session.refresh(url_entry)
                session.expunge(url_entry)  # Detach from session

                return url_entry

        except URLNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def list_all(self, limit: int = 100, offset: int = 0, user_id: Optional[str] = None) -> List[URLModel]:
        """
        List all URL entries.

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            user_id: Optional user ID filter

        Returns:
            List of URLModel entries

        Raises:
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                query = session.query(URLModel)

                if user_id:
                    query = query.filter(URLModel.user_id == user_id)

                query = query.order_by(URLModel.created_at.desc())
                query = query.limit(limit).offset(offset)

                results = query.all()
                # Expunge all objects from session so they can be used outside
                for url in results:
                    session.expunge(url)
                return results

        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e

    def count_all(self, user_id: Optional[str] = None) -> int:
        """
        Count total URL entries.

        Args:
            user_id: Optional user ID filter

        Returns:
            Total count

        Raises:
            DatabaseException: If database operation fails
        """
        try:
            with self.db_connection.get_session() as session:
                query = session.query(URLModel)

                if user_id:
                    query = query.filter(URLModel.user_id == user_id)

                return query.count()

        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error: {str(e)}") from e
