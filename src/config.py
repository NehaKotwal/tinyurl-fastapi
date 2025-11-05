"""
Configuration management using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Application Settings
    app_name: str = Field(default="URL Shortener Service", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Database Settings
    database_url: str = Field(default="sqlite:///./urls.db", alias="DATABASE_URL")

    # URL Settings
    base_url: str = Field(default="http://localhost:8000", alias="BASE_URL")
    short_code_length: int = Field(default=6, alias="SHORT_CODE_LENGTH")
    custom_alias_min_length: int = Field(default=4, alias="CUSTOM_ALIAS_MIN_LENGTH")
    custom_alias_max_length: int = Field(default=20, alias="CUSTOM_ALIAS_MAX_LENGTH")

    # Cache Settings
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")  # 1 hour
    cache_max_size: int = Field(default=1000, alias="CACHE_MAX_SIZE")
    cache_popular_threshold: int = Field(default=10, alias="CACHE_POPULAR_THRESHOLD")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=10, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # seconds

    # Security
    secret_key: str = Field(default="dev-secret-key", alias="SECRET_KEY")
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:8000", alias="ALLOWED_ORIGINS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_allowed_origins_list(self) -> List[str]:
        """Parse allowed origins string into list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


# Singleton instance
settings = Settings()
