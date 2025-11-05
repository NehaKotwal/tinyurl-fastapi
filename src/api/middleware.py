"""
Middleware for FastAPI application.
Includes rate limiting using token bucket algorithm.
"""
import time
from typing import Dict, Optional, Callable
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings
from src.utils.exceptions import RateLimitExceededException


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    Each IP gets a bucket with tokens that refill over time.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (requests)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens available, False otherwise
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_tokens(self) -> float:
        """Get current token count."""
        with self.lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Tracks buckets per IP address.
    """

    def __init__(self, requests: int, window: int):
        """
        Initialize rate limiter.

        Args:
            requests: Number of requests allowed
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self.refill_rate = requests / window  # tokens per second
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = Lock()

    def _get_or_create_bucket(self, key: str) -> TokenBucket:
        """
        Get or create bucket for a key.

        Args:
            key: Identifier (e.g., IP address)

        Returns:
            TokenBucket instance
        """
        with self.lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(
                    capacity=self.requests,
                    refill_rate=self.refill_rate
                )
            return self.buckets[key]

    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed for key.

        Args:
            key: Identifier (e.g., IP address)

        Returns:
            True if allowed, False if rate limited
        """
        bucket = self._get_or_create_bucket(key)
        return bucket.consume()

    def get_remaining(self, key: str) -> int:
        """
        Get remaining tokens for key.

        Args:
            key: Identifier

        Returns:
            Number of remaining tokens
        """
        bucket = self._get_or_create_bucket(key)
        return int(bucket.get_tokens())

    def cleanup_old_buckets(self):
        """Remove old buckets to prevent memory leaks."""
        with self.lock:
            # Remove buckets that are full (haven't been used)
            keys_to_remove = [
                key for key, bucket in self.buckets.items()
                if bucket.get_tokens() >= bucket.capacity
            ]
            for key in keys_to_remove[:len(keys_to_remove) // 2]:  # Remove half
                del self.buckets[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    Uses decorator pattern to wrap request handling.
    """

    def __init__(self, app, enabled: bool = True, requests: int = 10, window: int = 60):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            enabled: Whether rate limiting is enabled
            requests: Number of requests allowed
            window: Time window in seconds
        """
        super().__init__(app)
        self.enabled = enabled
        self.rate_limiter = RateLimiter(requests=requests, window=window)

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip rate limiting if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health check and docs
        if request.url.path in ['/health', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            )

        # Add rate limit headers
        response = await call_next(request)
        remaining = self.rate_limiter.get_remaining(client_ip)
        response.headers['X-RateLimit-Limit'] = str(self.rate_limiter.requests)
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Window'] = str(self.rate_limiter.window)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        # Check for forwarded IP (proxy)
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()

        # Check for real IP
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        # Fall back to client host
        return request.client.host if request.client else 'unknown'


# Decorator for route-level rate limiting
def rate_limit(requests: int = 10, window: int = 60):
    """
    Decorator for rate limiting specific routes.

    Args:
        requests: Number of requests allowed
        window: Time window in seconds

    Returns:
        Decorator function
    """
    limiter = RateLimiter(requests=requests, window=window)

    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            if settings.rate_limit_enabled:
                client_ip = request.client.host if request.client else 'unknown'

                if not limiter.is_allowed(client_ip):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later."
                    )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
