# Architecture Documentation

Detailed architecture and design decisions for the URL Shortener Service.

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Patterns](#design-patterns)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Database Design](#database-design)
6. [Caching Strategy](#caching-strategy)
7. [Rate Limiting](#rate-limiting)
8. [URL Encoding](#url-encoding)
9. [Scalability Considerations](#scalability-considerations)
10. [Security Considerations](#security-considerations)

---

## System Overview

The URL Shortener Service is built with a layered architecture following clean architecture principles:

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│              (FastAPI Routes & Middleware)               │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                    Business Layer                        │
│                   (URL Service)                          │
└───────────┬───────────────────────┬─────────────────────┘
            │                       │
┌───────────▼──────────┐  ┌────────▼────────────┐
│   Data Access Layer  │  │   Caching Layer     │
│   (Repository)       │  │   (Cache Manager)   │
└───────────┬──────────┘  └─────────────────────┘
            │
┌───────────▼──────────┐
│    Database Layer    │
│      (SQLite)        │
└──────────────────────┘
```

### Key Principles

- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Inversion**: Higher layers depend on abstractions, not implementations
- **Single Responsibility**: Each class has one reason to change
- **Open/Closed Principle**: Open for extension, closed for modification

---

## Design Patterns

### 1. Repository Pattern

**Location**: `src/repository/url_repository.py`

**Purpose**: Abstracts database operations and provides a clean interface for data access.

**Benefits**:
- Decouples business logic from data access
- Makes testing easier (can mock repository)
- Allows changing database without affecting business logic
- Centralizes database queries

**Implementation**:
```python
class URLRepository:
    def create(self, original_url, custom_alias=None, ...):
        # Database creation logic

    def get_by_short_code(self, short_code):
        # Database retrieval logic

    def update(self, short_code, original_url=None, ...):
        # Database update logic
```

### 2. Factory Pattern

**Location**: `src/services/encoder.py`

**Purpose**: Creates encoder instances without exposing creation logic.

**Benefits**:
- Supports multiple encoding strategies
- Easy to add new encoders
- Centralized encoder creation

**Implementation**:
```python
class URLEncoderFactory:
    _encoders = {
        'base62': Base62Encoder,
    }

    @classmethod
    def create_encoder(cls, encoder_type='base62'):
        encoder_class = cls._encoders.get(encoder_type)
        return encoder_class()
```

### 3. Singleton Pattern

**Location**:
- `src/repository/url_repository.py` (DatabaseConnection)
- `src/services/cache_service.py` (URLCacheManager)

**Purpose**: Ensures only one instance of database connection and cache manager exists.

**Benefits**:
- Prevents multiple database connections
- Single source of truth for cache
- Resource efficient

**Implementation**:
```python
class DatabaseConnection:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 4. Decorator Pattern

**Location**: `src/api/middleware.py`

**Purpose**: Adds rate limiting behavior without modifying core functionality.

**Benefits**:
- Adds functionality transparently
- Can be enabled/disabled easily
- Follows open/closed principle

**Implementation**:
```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            return error_response
        # Continue with request
        return await call_next(request)
```

### 5. Strategy Pattern

**Location**: `src/services/encoder.py`

**Purpose**: Allows different encoding algorithms to be used interchangeably.

**Benefits**:
- Easy to add new encoding strategies
- Runtime selection of encoder
- Follows open/closed principle

**Implementation**:
```python
class EncoderStrategy(Protocol):
    def encode(self, num: int) -> str: ...
    def decode(self, code: str) -> int: ...

class Base62Encoder:
    def encode(self, num): ...
    def decode(self, code): ...
```

---

## Component Architecture

### 1. API Layer

**Files**: `src/api/routes.py`, `src/api/middleware.py`

**Responsibilities**:
- Handle HTTP requests/responses
- Validate input data
- Apply rate limiting
- Error handling
- Return appropriate status codes

**Key Components**:
- **Routes**: Define API endpoints
- **Middleware**: Cross-cutting concerns (rate limiting, CORS)
- **Exception Handlers**: Convert exceptions to HTTP responses

### 2. Service Layer

**Files**: `src/services/url_service.py`

**Responsibilities**:
- Business logic orchestration
- Coordinate between repository and cache
- Implement URL shortening workflow
- Handle URL expiration logic

**Key Methods**:
- `shorten_url()`: Create shortened URL
- `get_original_url()`: Retrieve and track URL access
- `get_url_stats()`: Get analytics data
- `update_url()`: Modify existing URL
- `delete_url()`: Remove URL

### 3. Repository Layer

**Files**: `src/repository/url_repository.py`

**Responsibilities**:
- Database CRUD operations
- Query building
- Transaction management
- Error handling

**Key Methods**:
- `create()`: Insert new URL
- `get_by_short_code()`: Retrieve by short code
- `increment_click_count()`: Update statistics
- `list_all()`: Paginated retrieval

### 4. Cache Layer

**Files**: `src/services/cache_service.py`

**Responsibilities**:
- In-memory caching
- LRU eviction
- TTL management
- Cache statistics

**Key Components**:
- **LRUCache**: General-purpose LRU cache
- **URLCacheManager**: URL-specific cache logic
- **CacheEntry**: Cache entry with metadata

### 5. Encoder Service

**Files**: `src/services/encoder.py`

**Responsibilities**:
- Generate short codes
- Base62 encoding/decoding
- Collision handling

**Key Components**:
- **Base62Encoder**: Base62 algorithm
- **ShortCodeGenerator**: Short code generation
- **URLEncoderFactory**: Encoder creation

---

## Data Flow

### URL Shortening Flow

```
Client Request
    │
    ▼
┌────────────────┐
│  API Route     │ POST /shorten
│  (routes.py)   │
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  URL Service   │ shorten_url()
│  (url_service) │
└────────┬───────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐   ┌────────────┐
│  Validator      │   │ Repository │
│  (validators)   │   │            │
└─────────────────┘   └─────┬──────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  Database    │
                      │  (SQLite)    │
                      └──────────────┘
```

### URL Redirect Flow

```
Client Request
    │
    ▼
┌────────────────┐
│  API Route     │ GET /{short_code}
│  (routes.py)   │
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  URL Service   │ get_original_url()
│  (url_service) │
└────────┬───────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐   ┌────────────┐
│  Cache Manager  │   │ Repository │
│  (check cache)  │   │            │
└─────────────────┘   └─────┬──────┘
         │                   │
         │ (if miss)         ▼
         └─────────────►  Database
                            │
                            │ (increment counter)
                            ▼
                      ┌──────────────┐
                      │  Update      │
                      │  Cache       │
                      └──────────────┘
```

---

## Database Design

### URLs Table Schema

```sql
CREATE TABLE urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code VARCHAR(20) UNIQUE NOT NULL,
    original_url VARCHAR(2048) NOT NULL,
    custom_alias VARCHAR(50) UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    click_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at DATETIME,
    user_id VARCHAR(100)
);

-- Indexes
CREATE INDEX idx_short_code ON urls(short_code);
CREATE INDEX idx_custom_alias ON urls(custom_alias);
CREATE INDEX idx_user_id ON urls(user_id);
CREATE INDEX idx_short_code_created ON urls(short_code, created_at);
CREATE INDEX idx_user_created ON urls(user_id, created_at);
```

### Design Decisions

1. **Auto-incrementing ID**: Used for Base62 encoding
2. **Short Code**: Fixed-length indexed field for fast lookups
3. **Custom Alias**: Optional unique field for personalized URLs
4. **Composite Indexes**: For frequently queried combinations
5. **Expiration Support**: Nullable expires_at field
6. **Analytics Fields**: click_count and last_accessed_at

### Scaling Considerations

For PostgreSQL migration:
```sql
-- Use SERIAL for auto-increment
id SERIAL PRIMARY KEY,

-- Add partitioning for large datasets
PARTITION BY RANGE (created_at);

-- Add hash index for short_code
CREATE INDEX USING HASH ON urls(short_code);
```

---

## Caching Strategy

### LRU Cache Implementation

**Algorithm**: Least Recently Used (LRU)

**Structure**:
```python
OrderedDict {
    'short_code': CacheEntry(
        value='https://example.com',
        expires_at=timestamp,
        access_count=42
    )
}
```

### Caching Rules

1. **When to Cache**:
   - URL has >= 10 clicks (popular threshold)
   - After successful redirect

2. **When to Invalidate**:
   - URL is updated
   - URL is deleted
   - Cache entry expires (TTL)

3. **Eviction Policy**:
   - Remove least recently used when cache is full
   - Maximum size: 1000 entries
   - TTL: 1 hour per entry

### Cache Performance

**Hit Rate Formula**:
```
Hit Rate = (Cache Hits / Total Requests) * 100
```

**Expected Performance**:
- 70-80% hit rate for popular URLs
- Sub-millisecond response time for cache hits
- Reduces database load significantly

---

## Rate Limiting

### Token Bucket Algorithm

**How it Works**:
1. Each IP gets a bucket with tokens
2. Each request consumes 1 token
3. Tokens refill at constant rate
4. Request rejected if no tokens available

**Parameters**:
- Capacity: 10 tokens (max burst)
- Refill Rate: 10 tokens per 60 seconds
- Token Cost: 1 token per request

**Implementation**:
```python
class TokenBucket:
    def consume(self, tokens=1):
        self._refill()  # Add tokens based on time
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
```

### Benefits

- Allows burst traffic
- Fair distribution
- Per-IP tracking
- Prevents abuse

### Alternative Approaches

1. **Fixed Window**: Simpler but allows burst at window boundaries
2. **Sliding Window**: More accurate but memory intensive
3. **Leaky Bucket**: Constant rate, no bursts allowed

---

## URL Encoding

### Base62 Encoding

**Character Set**: `a-zA-Z0-9` (62 characters)

**Algorithm**:
```python
def encode(num):
    if num == 0:
        return 'a'

    result = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(ALPHABET[remainder])

    return ''.join(reversed(result))
```

**Capacity Calculation**:
- 6 characters: 62^6 = 56,800,235,584 URLs
- 7 characters: 62^7 = 3,521,614,606,208 URLs
- 8 characters: 62^8 = 218,340,105,584,896 URLs

### Why Base62?

**Advantages**:
- URL-safe (no special encoding)
- Case-sensitive (more combinations)
- Human-readable
- Short codes (6-8 characters)

**Alternatives Considered**:
- **Base64**: Contains special characters (+, /, =)
- **Base36**: Less combinations (36^6 vs 62^6)
- **UUID**: Too long (36 characters)
- **Hash-based**: Collision handling complexity

### Collision Handling

1. **Primary Strategy**: ID-based encoding (no collisions)
2. **Fallback**: Append suffix if needed
3. **Random Generation**: For custom scenarios

---

## Scalability Considerations

### Horizontal Scaling

**Stateless Design**:
- No session state in application
- All state in database/cache
- Can add more servers easily

**Load Balancing**:
```
        ┌──────────────┐
        │ Load Balancer│
        └──────┬───────┘
               │
       ┌───────┼───────┐
       │       │       │
   ┌───▼──┐ ┌──▼──┐ ┌─▼───┐
   │App 1 │ │App 2│ │App 3│
   └───┬──┘ └──┬──┘ └─┬───┘
       │       │      │
       └───────┼──────┘
               │
        ┌──────▼────────┐
        │   Database    │
        │  (PostgreSQL) │
        └───────────────┘
```

### Database Scaling

**Vertical Scaling**:
- Increase database server resources
- Add more CPU/RAM
- Use SSD storage

**Horizontal Scaling**:
- Read replicas for analytics
- Sharding by user_id or short_code
- Separate read/write connections

**Sharding Strategy**:
```python
# Example: Hash-based sharding
shard_id = hash(short_code) % num_shards
database = databases[shard_id]
```

### Cache Scaling

**Current**: In-memory cache (single server)

**Distributed Caching** (Future):
- Use Redis cluster
- Consistent hashing
- Replication for high availability

### Performance Targets

- **Latency**: < 50ms for redirects (cached)
- **Throughput**: 1000+ requests/second
- **Availability**: 99.9% uptime
- **Scalability**: Handle 1M+ URLs

---

## Security Considerations

### Input Validation

1. **URL Validation**:
   - Check URL format
   - Limit length (2048 chars)
   - Sanitize input

2. **Custom Alias Validation**:
   - Alphanumeric + hyphens/underscores
   - Length limits (4-20 chars)
   - Reserved keyword blocking

### SQL Injection Prevention

- Use parameterized queries
- ORM (SQLAlchemy) escaping
- No raw SQL with user input

### Rate Limiting

- Prevents DDoS attacks
- Limits abuse
- Per-IP tracking

### HTTPS

- Enforce HTTPS in production
- Redirect HTTP to HTTPS
- HSTS headers

### Additional Security Measures

1. **CORS**: Restrict origins
2. **Input Sanitization**: Strip malicious content
3. **Error Messages**: Don't leak sensitive info
4. **Monitoring**: Log suspicious activity
5. **Backup**: Regular database backups

---

## Testing Strategy

### Unit Tests

- Test individual components
- Mock dependencies
- Fast execution

**Coverage**:
- Encoder: Base62 logic
- Cache: LRU eviction, TTL
- Validators: URL and alias validation
- Repository: Database operations

### Integration Tests

- Test full request/response cycle
- Use test database
- Test API endpoints

**Coverage**:
- All HTTP endpoints
- Error handling
- Rate limiting behavior

### Performance Tests

**Tools**: Locust, pytest-benchmark

**Metrics**:
- Response time
- Throughput
- Cache hit rate
- Database query time

---

## Monitoring and Observability

### Metrics to Track

1. **Application Metrics**:
   - Request count
   - Response time
   - Error rate
   - Cache hit rate

2. **Business Metrics**:
   - URLs created
   - Redirects performed
   - Popular URLs
   - User activity

3. **Infrastructure Metrics**:
   - CPU usage
   - Memory usage
   - Database connections
   - Network I/O

### Logging

**Log Levels**:
- ERROR: Application errors
- WARNING: Unusual events
- INFO: Normal operations
- DEBUG: Detailed debugging

**Structured Logging**:
```python
logger.info(
    "URL created",
    extra={
        "short_code": "aB3xY9",
        "user_id": "user123",
        "timestamp": datetime.utcnow()
    }
)
```

---

## Future Enhancements

### Short-term

1. User authentication (JWT)
2. API key management
3. Redis integration
4. Docker containerization

### Medium-term

1. Analytics dashboard
2. Geographic tracking
3. QR code generation
4. Bulk operations

### Long-term

1. Microservices architecture
2. Event-driven design
3. Machine learning for fraud detection
4. Global CDN integration

---

## References

- **Clean Architecture** by Robert C. Martin
- **Domain-Driven Design** by Eric Evans
- **Designing Data-Intensive Applications** by Martin Kleppmann
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org

---

For API details, see [API.md](API.md). For usage instructions, see [README.md](../README.md).
