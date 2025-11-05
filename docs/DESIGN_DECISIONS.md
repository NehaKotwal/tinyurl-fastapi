# Design Decisions

This document explains the key design decisions made during the development of the URL Shortener Service and the rationale behind them.

## Table of Contents

1. [Technology Choices](#technology-choices)
2. [Encoding Algorithm](#encoding-algorithm)
3. [Caching Strategy](#caching-strategy)
4. [Rate Limiting Approach](#rate-limiting-approach)
5. [Database Design](#database-design)
6. [API Design](#api-design)
7. [Testing Strategy](#testing-strategy)
8. [Trade-offs](#trade-offs)

---

## Technology Choices

### Why FastAPI?

**Decision**: Use FastAPI over Flask or Django

**Rationale**:
- Modern async/await support
- Automatic API documentation (OpenAPI/Swagger)
- Built-in data validation with Pydantic
- High performance (comparable to Node.js)
- Type hints for better IDE support
- Active community and development

**Alternatives Considered**:
- **Flask**: More mature but lacks async support and built-in validation
- **Django**: Overkill for this use case, includes unnecessary features
- **Express.js**: Would require Node.js, team has Python expertise

### Why SQLAlchemy?

**Decision**: Use SQLAlchemy ORM

**Rationale**:
- Database abstraction layer
- Easy to switch databases (SQLite → PostgreSQL)
- Prevents SQL injection
- Migration support (Alembic)
- Connection pooling

**Alternatives Considered**:
- **Raw SQL**: More control but error-prone, no abstraction
- **Django ORM**: Tied to Django framework
- **Peewee**: Less feature-rich, smaller community

### Why SQLite for Development?

**Decision**: Use SQLite for development, PostgreSQL for production

**Rationale**:
- Zero configuration for development
- Single file database (easy to reset)
- Sufficient for testing
- Easy migration path to PostgreSQL

**Production Database**: PostgreSQL
- Better concurrency support
- More advanced features (JSON, full-text search)
- Proven scalability

---

## Encoding Algorithm

### Why Base62?

**Decision**: Use Base62 encoding (a-z, A-Z, 0-9)

**Rationale**:
1. **URL-safe**: No special characters requiring encoding
2. **Compact**: 62^6 = 56 billion combinations in 6 characters
3. **Human-readable**: Easy to type and remember
4. **Case-sensitive**: More combinations than Base36

**Comparison**:

| Encoding | Characters | 6-char Capacity | URL-safe | Readable |
|----------|------------|-----------------|----------|----------|
| Base36   | 36         | 2.1 billion     | ✓        | ✓        |
| Base62   | 62         | 56.8 billion    | ✓        | ✓        |
| Base64   | 64         | 68.7 billion    | ✗ (+,/)  | ✓        |
| UUID     | 16 (hex)   | Unlimited       | ✓        | ✗ (long) |

**Alternatives Considered**:
- **Base64**: Contains '+' and '/' which require URL encoding
- **Base36**: Fewer combinations, would need longer codes
- **Hash-based (MD5/SHA)**: Collision handling complexity
- **UUID**: 36 characters, not user-friendly

### ID-based vs Hash-based

**Decision**: ID-based encoding using database auto-increment

**Rationale**:
- **No collisions**: Each ID is unique
- **Simple**: Straightforward implementation
- **Predictable length**: Can control by adjusting minimum length
- **Fast**: O(1) encoding/decoding

**Hash-based Approach (Not Chosen)**:
```python
# Hash the URL and take first N characters
short_code = md5(url).hexdigest()[:6]
```

**Why Not**:
- Collision possibility (birthday paradox)
- Requires collision handling logic
- Same URL creates same hash (predictable)
- Harder to control code length

---

## Caching Strategy

### Why LRU Cache?

**Decision**: Implement LRU (Least Recently Used) cache

**Rationale**:
- **Self-regulating**: Automatically evicts unused items
- **No manual cleanup**: Memory bounded by max size
- **Hot data**: Keeps frequently accessed URLs
- **Simple**: Easy to understand and implement

**Cache Rules**:
1. Only cache URLs with ≥10 clicks (popularity threshold)
2. Default TTL of 1 hour
3. Maximum 1000 entries
4. Invalidate on update/delete

**Alternatives Considered**:
- **LFU (Least Frequently Used)**: More complex, requires frequency tracking
- **FIFO**: Doesn't consider access patterns
- **Random Eviction**: No optimization for hot data
- **Redis**: Overkill for initial version, adds dependency

### Why In-Memory Cache?

**Decision**: Start with in-memory cache, plan for Redis later

**Rationale**:
- **Simplicity**: No external dependencies
- **Fast**: Nanosecond access time
- **Development**: Easy to test and debug
- **Migration Path**: Can switch to Redis without changing interface

**When to Switch to Redis**:
- Multiple application servers (horizontal scaling)
- Need for persistence across restarts
- Distributed cache invalidation
- Advanced features (pub/sub, etc.)

---

## Rate Limiting Approach

### Why Token Bucket?

**Decision**: Implement token bucket algorithm

**Rationale**:
- **Burst handling**: Allows temporary bursts
- **Fair**: Smooths out traffic over time
- **Standard**: Well-understood algorithm
- **Configurable**: Easy to adjust limits

**How It Works**:
```
Bucket capacity: 10 tokens
Refill rate: 10 tokens/60 seconds
Request cost: 1 token

User makes burst of 10 requests → All succeed
11th request within 60s → Rejected
After 6 seconds → 1 token refilled
```

**Alternatives Considered**:

1. **Fixed Window**
   - ❌ Allows bursts at window boundaries
   - ✓ Simple implementation

2. **Sliding Window**
   - ✓ More accurate
   - ❌ Higher memory usage

3. **Leaky Bucket**
   - ✓ Constant rate
   - ❌ No burst allowance

**Why Token Bucket Won**:
- Balance between accuracy and complexity
- Burst handling important for user experience
- Industry standard (AWS, GitHub use it)

### Per-IP vs Per-User

**Decision**: Rate limit by IP address (for now)

**Rationale**:
- **Simple**: No authentication required
- **Effective**: Prevents most abuse
- **Privacy**: No user tracking needed

**Future Enhancement**: Per-user rate limiting with authentication
- More accurate attribution
- Custom limits per tier
- Better analytics

---

## Database Design

### Single Table vs Multiple Tables

**Decision**: Single `urls` table with optional user_id

**Rationale**:
- **Simplicity**: KISS principle
- **Performance**: No joins for basic operations
- **Sufficient**: Meets all current requirements

**Future Consideration**: Separate users table when authentication is added
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    api_key VARCHAR(100),
    created_at DATETIME
);

-- Add foreign key to urls table
ALTER TABLE urls ADD CONSTRAINT fk_user
    FOREIGN KEY (user_id) REFERENCES users(id);
```

### Indexes

**Decision**: Index short_code, custom_alias, and user_id

**Rationale**:
- **short_code**: Primary lookup field (redirects)
- **custom_alias**: Alternative lookup field
- **user_id**: For listing user's URLs
- **Composite indexes**: For common query patterns

**Trade-off**:
- ✓ Fast reads (O(log n) instead of O(n))
- ❌ Slower writes (must update indexes)
- ❌ More storage space

**Decision**: Worth it because reads >> writes in this application

---

## API Design

### REST vs GraphQL

**Decision**: Use RESTful API

**Rationale**:
- **Simplicity**: Standard HTTP methods
- **Familiarity**: Most developers know REST
- **Caching**: Standard HTTP caching works
- **Tools**: Wide ecosystem support

**GraphQL (Not Chosen)**:
- Overkill for simple CRUD operations
- Over-fetching not a problem (small payloads)
- Additional complexity

### HTTP Methods

**Decision**: Follow REST conventions

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create    | POST   | /shorten |
| Read      | GET    | /{code}  |
| Update    | PUT    | /api/urls/{code} |
| Delete    | DELETE | /api/urls/{code} |
| List      | GET    | /api/urls |

### API Versioning

**Decision**: No versioning initially, plan for /v1/ prefix later

**Rationale**:
- Start simple (YAGNI principle)
- Can add versioning when breaking changes needed
- Use semantic versioning in response headers

**Migration Path**:
```
Current: /shorten
Future:  /v1/shorten
         /v2/shorten (with breaking changes)
```

### Error Response Format

**Decision**: Use standard HTTP status codes with JSON body

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

**Rationale**:
- Standard HTTP status codes
- Detailed error messages
- Machine-readable error codes
- Consistent format

---

## Testing Strategy

### pytest vs unittest

**Decision**: Use pytest

**Rationale**:
- Simpler syntax (assert vs self.assertEqual)
- Better fixtures
- Rich plugin ecosystem
- FastAPI officially supports pytest

### Test Organization

**Decision**: Mirror source structure in tests/

```
src/services/encoder.py → tests/test_encoder.py
```

**Rationale**:
- Easy to find corresponding tests
- Clear organization
- Standard convention

### Coverage Target

**Decision**: Aim for 80%+ coverage, but don't chase 100%

**Rationale**:
- 80% covers most critical paths
- Diminishing returns after 80%
- 100% coverage doesn't guarantee bug-free
- Focus on meaningful tests, not coverage numbers

### Integration vs Unit Tests

**Decision**: Both, with emphasis on integration tests for API

**Rationale**:
- Unit tests: Fast, isolated, test business logic
- Integration tests: Test full request/response cycle
- API integration tests most valuable for this service

---

## Trade-offs

### Performance vs Simplicity

**Decision**: Favor simplicity initially, optimize later

**Examples**:
- In-memory cache before Redis
- SQLite before PostgreSQL
- Synchronous operations before async (where not needed)

**Rationale**:
- Premature optimization is evil
- Simple code is maintainable
- Can optimize bottlenecks when identified

### Features vs Time-to-Market

**Decision**: MVP first, advanced features later

**MVP Features**:
- ✓ URL shortening
- ✓ Custom aliases
- ✓ Basic analytics
- ✓ Rate limiting
- ✓ Caching

**Future Features**:
- ⏳ User authentication
- ⏳ QR codes
- ⏳ Advanced analytics
- ⏳ Geographic tracking

### Consistency vs Availability

**Decision**: Favor consistency (ACID transactions)

**Rationale**:
- URL shortener needs strong consistency
- Can't have duplicate short codes
- Eventual consistency would be problematic

**Example**:
```python
# Transaction ensures atomicity
with session.begin():
    url = create_url(...)
    short_code = generate_code(url.id)
    url.short_code = short_code
    session.commit()
```

### Security vs Usability

**Decision**: Balance security with ease of use

**Examples**:
- Rate limiting: 10/min (not too strict)
- Custom aliases: Allow but validate
- HTTPS: Enforce in production only

**Rationale**:
- Too strict: Poor user experience
- Too loose: Security risks
- Find middle ground

---

## Lessons Learned

1. **Start Simple**: In-memory cache → Redis later
2. **Design for Change**: Repository pattern makes DB switching easy
3. **Test Early**: Catch issues before production
4. **Document Decisions**: This file helps future maintainers
5. **Measure First**: Don't optimize without profiling

---

## Future Decisions to Make

1. **Authentication**: OAuth2? JWT? API Keys?
2. **Caching**: When to move to Redis?
3. **Database**: When to migrate to PostgreSQL?
4. **Deployment**: Docker? Kubernetes? Serverless?
5. **Monitoring**: Prometheus? DataDog? New Relic?

---

## References

- [Designing Data-Intensive Applications](https://dataintensive.net/)
- [RESTful API Design](https://restfulapi.net/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

For technical details, see [ARCHITECTURE.md](ARCHITECTURE.md). For API usage, see [API.md](API.md).
