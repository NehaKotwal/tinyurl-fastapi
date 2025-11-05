"""
Custom exceptions for the URL shortener service.
"""


class URLShortenerException(Exception):
    """Base exception for URL shortener."""

    pass


class URLNotFoundException(URLShortenerException):
    """Raised when a short code is not found."""

    pass


class URLExpiredException(URLShortenerException):
    """Raised when a URL has expired."""

    pass


class CustomAliasAlreadyExistsException(URLShortenerException):
    """Raised when a custom alias already exists."""

    pass


class InvalidURLException(URLShortenerException):
    """Raised when URL validation fails."""

    pass


class InvalidCustomAliasException(URLShortenerException):
    """Raised when custom alias validation fails."""

    pass


class RateLimitExceededException(URLShortenerException):
    """Raised when rate limit is exceeded."""

    pass


class DatabaseException(URLShortenerException):
    """Raised when database operations fail."""

    pass
