"""
URL encoding service using Base62 algorithm.
Implements Strategy pattern for different encoding strategies.
"""
import string
import random
from abc import ABC, abstractmethod
from typing import Protocol


class EncoderStrategy(Protocol):
    """Protocol for encoder strategies."""

    def encode(self, num: int) -> str:
        """Encode a number to a short string."""
        ...

    def decode(self, code: str) -> int:
        """Decode a short string back to a number."""
        ...


class Base62Encoder:
    """
    Base62 encoder using alphanumeric characters (a-z, A-Z, 0-9).
    Implements Strategy pattern for encoding.
    """

    # Base62 character set: 62 characters (a-z, A-Z, 0-9)
    ALPHABET = string.ascii_letters + string.digits  # a-zA-Z0-9
    BASE = len(ALPHABET)

    def encode(self, num: int) -> str:
        """
        Encode a positive integer to a Base62 string.

        Args:
            num: Positive integer to encode

        Returns:
            Base62 encoded string

        Example:
            >>> encoder = Base62Encoder()
            >>> encoder.encode(12345)
            'dnh'
        """
        if num == 0:
            return self.ALPHABET[0]

        encoded = []
        while num > 0:
            num, remainder = divmod(num, self.BASE)
            encoded.append(self.ALPHABET[remainder])

        return ''.join(reversed(encoded))

    def decode(self, code: str) -> int:
        """
        Decode a Base62 string back to an integer.

        Args:
            code: Base62 encoded string

        Returns:
            Decoded integer

        Example:
            >>> encoder = Base62Encoder()
            >>> encoder.decode('dnh')
            12345
        """
        num = 0
        for char in code:
            num = num * self.BASE + self.ALPHABET.index(char)
        return num

    def encode_with_length(self, num: int, min_length: int = 6) -> str:
        """
        Encode a number and pad to minimum length.

        Args:
            num: Number to encode
            min_length: Minimum length of encoded string

        Returns:
            Base62 encoded string with minimum length
        """
        encoded = self.encode(num)
        if len(encoded) < min_length:
            # Pad with first character to reach minimum length
            encoded = self.ALPHABET[0] * (min_length - len(encoded)) + encoded
        return encoded


class URLEncoderFactory:
    """
    Factory pattern for creating URL encoders.
    Makes it easy to switch between different encoding strategies.
    """

    _encoders = {
        'base62': Base62Encoder,
    }

    @classmethod
    def create_encoder(cls, encoder_type: str = 'base62') -> Base62Encoder:
        """
        Create an encoder instance.

        Args:
            encoder_type: Type of encoder ('base62' is default)

        Returns:
            Encoder instance

        Raises:
            ValueError: If encoder type is not supported
        """
        encoder_class = cls._encoders.get(encoder_type)
        if not encoder_class:
            raise ValueError(f"Unsupported encoder type: {encoder_type}")
        return encoder_class()

    @classmethod
    def register_encoder(cls, name: str, encoder_class):
        """
        Register a new encoder strategy.

        Args:
            name: Name for the encoder
            encoder_class: Encoder class to register
        """
        cls._encoders[name] = encoder_class


class ShortCodeGenerator:
    """
    Generates short codes for URLs.
    Uses Base62 encoder and handles collision scenarios.
    """

    def __init__(self, encoder: Base62Encoder = None, min_length: int = 6):
        """
        Initialize short code generator.

        Args:
            encoder: Encoder instance (defaults to Base62)
            min_length: Minimum length of short codes
        """
        self.encoder = encoder or Base62Encoder()
        self.min_length = min_length

    def generate_from_id(self, url_id: int) -> str:
        """
        Generate short code from URL ID.

        Args:
            url_id: Database ID of URL

        Returns:
            Short code string
        """
        return self.encoder.encode_with_length(url_id, self.min_length)

    def generate_random(self, length: int = 6) -> str:
        """
        Generate a random short code.
        Useful as fallback for collision resolution.

        Args:
            length: Length of random code

        Returns:
            Random short code
        """
        return ''.join(random.choices(self.encoder.ALPHABET, k=length))

    def generate_with_retry(self, url_id: int, retry_suffix: int = 0) -> str:
        """
        Generate short code with retry mechanism for collision handling.

        Args:
            url_id: Database ID
            retry_suffix: Retry counter to append

        Returns:
            Short code with retry suffix if needed
        """
        base_code = self.generate_from_id(url_id)
        if retry_suffix > 0:
            suffix = self.encoder.encode(retry_suffix)
            return base_code + suffix
        return base_code


# Singleton instance for easy access
_default_generator = ShortCodeGenerator()


def generate_short_code(url_id: int, min_length: int = 6) -> str:
    """
    Convenience function to generate short code.

    Args:
        url_id: Database ID of URL
        min_length: Minimum length

    Returns:
        Generated short code
    """
    generator = ShortCodeGenerator(min_length=min_length)
    return generator.generate_from_id(url_id)
