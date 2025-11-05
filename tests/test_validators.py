"""
Unit tests for validators.
"""
import pytest
from src.utils.validators import validate_url, validate_custom_alias, sanitize_url
from src.utils.exceptions import InvalidURLException


class TestValidateURL:
    """Test URL validation."""

    def test_valid_urls(self):
        """Test validation of valid URLs."""
        valid_urls = [
            'https://www.example.com',
            'http://example.com',
            'https://example.com/path/to/page',
            'https://subdomain.example.com',
            'https://example.com?param=value',
            'https://example.com:8080/path',
        ]

        for url in valid_urls:
            is_valid, error = validate_url(url)
            assert is_valid, f"Expected {url} to be valid, got error: {error}"
            assert error == ""

    def test_urls_without_scheme(self):
        """Test URLs without scheme (should be valid after adding scheme)."""
        urls = [
            'www.example.com',
            'example.com',
            'subdomain.example.com',
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            # Should be valid because validator adds https:// prefix
            assert is_valid, f"Expected {url} to be valid after adding scheme"

    def test_invalid_urls(self):
        """Test validation of invalid URLs."""
        invalid_urls = [
            '',
            '   ',
            'not a url',
            'ht!tp://invalid',
        ]

        for url in invalid_urls:
            is_valid, error = validate_url(url)
            assert not is_valid, f"Expected {url} to be invalid"
            assert error != ""

    def test_url_too_long(self):
        """Test URL that exceeds maximum length."""
        long_url = 'https://example.com/' + 'a' * 2050
        is_valid, error = validate_url(long_url)
        assert not is_valid
        assert 'too long' in error.lower()


class TestValidateCustomAlias:
    """Test custom alias validation."""

    def test_valid_aliases(self):
        """Test validation of valid custom aliases."""
        valid_aliases = [
            'mylink',
            'my-link',
            'my_link',
            'MyLink123',
            'link-2024',
            'a1b2c3d4',
        ]

        for alias in valid_aliases:
            is_valid, error = validate_custom_alias(alias)
            assert is_valid, f"Expected {alias} to be valid, got error: {error}"
            assert error == ""

    def test_alias_too_short(self):
        """Test alias that is too short."""
        is_valid, error = validate_custom_alias('abc', min_length=4)
        assert not is_valid
        assert 'at least' in error.lower()

    def test_alias_too_long(self):
        """Test alias that is too long."""
        long_alias = 'a' * 25
        is_valid, error = validate_custom_alias(long_alias, max_length=20)
        assert not is_valid
        assert 'at most' in error.lower()

    def test_alias_invalid_characters(self):
        """Test alias with invalid characters."""
        invalid_aliases = [
            'my link',  # space
            'my@link',  # special char
            'my.link',  # dot
            'my/link',  # slash
            'my\\link',  # backslash
        ]

        for alias in invalid_aliases:
            is_valid, error = validate_custom_alias(alias)
            assert not is_valid, f"Expected {alias} to be invalid"
            assert 'can only contain' in error.lower()

    def test_reserved_keywords(self):
        """Test that reserved keywords are rejected."""
        reserved = ['api', 'admin', 'docs', 'health', 'static']

        for keyword in reserved:
            is_valid, error = validate_custom_alias(keyword)
            assert not is_valid
            assert 'reserved' in error.lower()

    def test_empty_alias(self):
        """Test that empty alias is valid (optional field)."""
        is_valid, error = validate_custom_alias('')
        assert is_valid
        assert error == ""

    def test_none_alias(self):
        """Test that None alias is valid (optional field)."""
        is_valid, error = validate_custom_alias(None)
        assert is_valid
        assert error == ""


class TestSanitizeURL:
    """Test URL sanitization."""

    def test_sanitize_valid_url(self):
        """Test sanitizing valid URL."""
        url = 'https://www.example.com'
        result = sanitize_url(url)
        assert result == url

    def test_sanitize_url_without_scheme(self):
        """Test that scheme is added to URL without one."""
        url = 'www.example.com'
        result = sanitize_url(url)
        assert result == 'https://www.example.com'

    def test_sanitize_url_with_whitespace(self):
        """Test that whitespace is stripped."""
        url = '  https://www.example.com  '
        result = sanitize_url(url)
        assert result == 'https://www.example.com'

    def test_sanitize_empty_url(self):
        """Test that empty URL raises exception."""
        with pytest.raises(InvalidURLException):
            sanitize_url('')

    def test_sanitize_invalid_url(self):
        """Test that invalid URL raises exception."""
        with pytest.raises(InvalidURLException):
            sanitize_url('not a valid url')

    def test_sanitize_none_url(self):
        """Test that None URL raises exception."""
        with pytest.raises(InvalidURLException):
            sanitize_url(None)
