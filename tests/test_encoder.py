"""
Unit tests for URL encoder service.
"""
import pytest
from src.services.encoder import Base62Encoder, ShortCodeGenerator, URLEncoderFactory


class TestBase62Encoder:
    """Test Base62 encoding."""

    def setup_method(self):
        """Set up test fixtures."""
        self.encoder = Base62Encoder()

    def test_encode_zero(self):
        """Test encoding zero."""
        result = self.encoder.encode(0)
        assert result == 'a'

    def test_encode_positive_numbers(self):
        """Test encoding positive numbers."""
        test_cases = [
            (1, 'b'),
            (10, 'k'),
            (100, 'bM'),
            (1000, 'qi'),
            (12345, 'dnh'),
        ]

        for num, expected in test_cases:
            result = self.encoder.encode(num)
            assert result == expected, f"Expected {expected} for {num}, got {result}"

    def test_decode_strings(self):
        """Test decoding strings."""
        test_cases = [
            ('a', 0),
            ('b', 1),
            ('k', 10),
            ('bM', 100),
            ('qi', 1000),
            ('dnh', 12345),
        ]

        for code, expected in test_cases:
            result = self.encoder.decode(code)
            assert result == expected, f"Expected {expected} for {code}, got {result}"

    def test_encode_decode_roundtrip(self):
        """Test encode-decode round trip."""
        test_numbers = [0, 1, 10, 100, 1000, 12345, 999999]

        for num in test_numbers:
            encoded = self.encoder.encode(num)
            decoded = self.encoder.decode(encoded)
            assert decoded == num, f"Round trip failed for {num}"

    def test_encode_with_length(self):
        """Test encoding with minimum length."""
        result = self.encoder.encode_with_length(1, min_length=6)
        assert len(result) == 6
        assert result == 'aaaaab'

    def test_encode_with_length_already_long(self):
        """Test encoding when already meets minimum length."""
        result = self.encoder.encode_with_length(999999, min_length=4)
        assert len(result) >= 4


class TestShortCodeGenerator:
    """Test short code generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ShortCodeGenerator(min_length=6)

    def test_generate_from_id(self):
        """Test generating short code from ID."""
        result = self.generator.generate_from_id(12345)
        assert len(result) >= 6
        assert isinstance(result, str)

    def test_generate_random(self):
        """Test generating random short code."""
        result = self.generator.generate_random(length=8)
        assert len(result) == 8
        assert isinstance(result, str)

    def test_generate_random_uniqueness(self):
        """Test that random codes are different."""
        codes = [self.generator.generate_random() for _ in range(100)]
        # Most should be unique (allowing for small chance of collision)
        assert len(set(codes)) > 90

    def test_generate_with_retry(self):
        """Test generating with retry suffix."""
        base_code = self.generator.generate_with_retry(12345, retry_suffix=0)
        retry_code = self.generator.generate_with_retry(12345, retry_suffix=1)

        assert base_code != retry_code
        assert len(retry_code) > len(base_code)

    def test_consistent_generation(self):
        """Test that same ID produces same code."""
        code1 = self.generator.generate_from_id(12345)
        code2 = self.generator.generate_from_id(12345)
        assert code1 == code2


class TestURLEncoderFactory:
    """Test URL encoder factory."""

    def test_create_base62_encoder(self):
        """Test creating Base62 encoder."""
        encoder = URLEncoderFactory.create_encoder('base62')
        assert isinstance(encoder, Base62Encoder)

    def test_create_default_encoder(self):
        """Test creating default encoder."""
        encoder = URLEncoderFactory.create_encoder()
        assert isinstance(encoder, Base62Encoder)

    def test_create_invalid_encoder(self):
        """Test creating invalid encoder type."""
        with pytest.raises(ValueError):
            URLEncoderFactory.create_encoder('invalid')

    def test_register_custom_encoder(self):
        """Test registering custom encoder."""

        class CustomEncoder:
            def encode(self, num):
                return str(num)

            def decode(self, code):
                return int(code)

        URLEncoderFactory.register_encoder('custom', CustomEncoder)
        encoder = URLEncoderFactory.create_encoder('custom')
        assert isinstance(encoder, CustomEncoder)
