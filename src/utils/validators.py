"""
Validation utilities for URL shortener.
"""
import re
import validators
from typing import Tuple
from src.utils.exceptions import InvalidURLException, InvalidCustomAliasException


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate if a string is a valid URL.

    Args:
        url: URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or len(url.strip()) == 0:
        return False, "URL cannot be empty"

    url = url.strip()

    # Check length
    if len(url) > 2048:
        return False, "URL is too long (max 2048 characters)"

    # Ensure URL has a scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Validate using validators library
    if not validators.url(url):
        return False, "Invalid URL format"

    return True, ""


def validate_custom_alias(alias: str, min_length: int = 4, max_length: int = 20) -> Tuple[bool, str]:
    """
    Validate custom alias format.

    Args:
        alias: Custom alias to validate
        min_length: Minimum length (default 4)
        max_length: Maximum length (default 20)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not alias:
        return True, ""  # Optional field

    alias = alias.strip()

    # Reserved keywords (check first, regardless of length)
    reserved = {'api', 'admin', 'health', 'docs', 'redoc', 'openapi', 'static', 'assets'}
    if alias.lower() in reserved:
        return False, f"'{alias}' is a reserved keyword and cannot be used as a custom alias"

    # Check length
    if len(alias) < min_length:
        return False, f"Custom alias must be at least {min_length} characters"

    if len(alias) > max_length:
        return False, f"Custom alias must be at most {max_length} characters"

    # Check format: only alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', alias):
        return False, "Custom alias can only contain letters, numbers, hyphens, and underscores"

    return True, ""


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by adding scheme if missing and stripping whitespace.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL

    Raises:
        InvalidURLException: If URL is invalid
    """
    if not url:
        raise InvalidURLException("URL cannot be empty")

    url = url.strip()

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Validate
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        raise InvalidURLException(error_msg)

    return url
