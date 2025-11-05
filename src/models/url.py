"""
Database models and Pydantic schemas for URL shortener.
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
import re

Base = declarative_base()


class URLModel(Base):
    """SQLAlchemy model for URL table."""

    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    short_code = Column(String(20), unique=True, index=True, nullable=True)  # Nullable during creation
    original_url = Column(String(2048), nullable=False)
    custom_alias = Column(String(50), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    click_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    user_id = Column(String(100), nullable=True, index=True)

    # Create composite index for frequently queried columns
    __table_args__ = (
        Index('idx_short_code_created', 'short_code', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )


# Pydantic Models for API validation

class URLCreate(BaseModel):
    """Schema for creating a shortened URL."""

    original_url: str = Field(..., description="The original long URL to shorten")
    custom_alias: Optional[str] = Field(None, description="Optional custom alias for the short URL")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration datetime")
    user_id: Optional[str] = Field(None, description="Optional user identifier")

    @validator('original_url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('URL cannot be empty')

        # Ensure URL has a scheme
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v

        # Basic URL validation
        if len(v) > 2048:
            raise ValueError('URL is too long (max 2048 characters)')

        return v

    @validator('custom_alias')
    def validate_custom_alias(cls, v):
        """Validate custom alias format."""
        if v is not None:
            v = v.strip()
            if len(v) < 4:
                raise ValueError('Custom alias must be at least 4 characters')
            if len(v) > 20:
                raise ValueError('Custom alias must be at most 20 characters')
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Custom alias can only contain letters, numbers, hyphens, and underscores')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "original_url": "https://www.example.com/very/long/url/path",
                "custom_alias": "my-link",
                "expires_at": "2024-12-31T23:59:59",
                "user_id": "user123"
            }
        }


class URLUpdate(BaseModel):
    """Schema for updating a shortened URL."""

    original_url: Optional[str] = Field(None, description="New destination URL")
    expires_at: Optional[datetime] = Field(None, description="New expiration datetime")

    @validator('original_url')
    def validate_url(cls, v):
        """Validate URL format."""
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('URL cannot be empty')

            if not v.startswith(('http://', 'https://')):
                v = 'https://' + v

            if len(v) > 2048:
                raise ValueError('URL is too long (max 2048 characters)')

        return v


class URLResponse(BaseModel):
    """Schema for URL response."""

    id: int
    short_code: str
    original_url: str
    custom_alias: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    click_count: int
    last_accessed_at: Optional[datetime]
    short_url: str

    class Config:
        from_attributes = True


class URLStats(BaseModel):
    """Schema for URL statistics."""

    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
    last_accessed_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_expired: bool

    class Config:
        from_attributes = True


class ShortenResponse(BaseModel):
    """Schema for shorten endpoint response."""

    short_code: str
    short_url: str
    original_url: str
    custom_alias: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        json_schema_extra = {
            "example": {
                "short_code": "aB3xY9",
                "short_url": "http://localhost:8000/aB3xY9",
                "original_url": "https://www.example.com/very/long/url",
                "custom_alias": None,
                "created_at": "2024-01-01T12:00:00",
                "expires_at": None
            }
        }
