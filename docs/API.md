# API Documentation

Complete API reference for the URL Shortener Service.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. Future versions will include API key authentication.

## Rate Limiting

- **Limit**: 10 requests per minute per IP address
- **Window**: 60 seconds
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Window`: Time window in seconds

When rate limit is exceeded:
```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

## Endpoints

### 1. Shorten URL

Create a shortened URL from a long URL.

**Endpoint**: `POST /shorten`

**Request Body**:
```json
{
  "original_url": "https://www.example.com/very/long/url",
  "custom_alias": "my-link",  // Optional
  "expires_at": "2024-12-31T23:59:59",  // Optional
  "user_id": "user123"  // Optional
}
```

**Response** (201 Created):
```json
{
  "short_code": "aB3xY9",
  "short_url": "http://localhost:8000/aB3xY9",
  "original_url": "https://www.example.com/very/long/url",
  "custom_alias": "my-link",
  "created_at": "2024-01-01T12:00:00",
  "expires_at": "2024-12-31T23:59:59"
}
```

**Error Responses**:

- **400 Bad Request** - Invalid URL or custom alias
  ```json
  {
    "detail": "Invalid URL format"
  }
  ```

- **409 Conflict** - Custom alias already exists
  ```json
  {
    "detail": "Custom alias 'my-link' already exists"
  }
  ```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://www.example.com",
    "custom_alias": "my-link"
  }'
```

---

### 2. Redirect to Original URL

Redirect to the original URL using short code or custom alias.

**Endpoint**: `GET /{short_code}`

**Parameters**:
- `short_code` (path) - The short code or custom alias

**Response** (307 Temporary Redirect):
- Redirects to original URL
- Increments click counter
- Updates last accessed timestamp

**Error Responses**:

- **404 Not Found** - Short code doesn't exist
  ```json
  {
    "detail": "Short URL 'abc123' not found"
  }
  ```

- **410 Gone** - URL has expired
  ```json
  {
    "detail": "Short URL 'abc123' has expired"
  }
  ```

**cURL Example**:
```bash
curl -L "http://localhost:8000/aB3xY9"
```

---

### 3. List All URLs

Get a paginated list of all shortened URLs.

**Endpoint**: `GET /api/urls`

**Query Parameters**:
- `limit` (integer, optional) - Maximum URLs to return (default: 100, max: 1000)
- `offset` (integer, optional) - Number of URLs to skip (default: 0)
- `user_id` (string, optional) - Filter by user ID

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "short_code": "aB3xY9",
    "original_url": "https://www.example.com",
    "custom_alias": "my-link",
    "created_at": "2024-01-01T12:00:00",
    "expires_at": null,
    "click_count": 42,
    "last_accessed_at": "2024-01-15T10:30:00",
    "short_url": "http://localhost:8000/aB3xY9"
  },
  {
    "id": 2,
    "short_code": "xY9aB3",
    "original_url": "https://www.example2.com",
    "custom_alias": null,
    "created_at": "2024-01-02T14:00:00",
    "expires_at": "2024-12-31T23:59:59",
    "click_count": 15,
    "last_accessed_at": "2024-01-14T08:20:00",
    "short_url": "http://localhost:8000/xY9aB3"
  }
]
```

**cURL Example**:
```bash
curl "http://localhost:8000/api/urls?limit=10&offset=0"
```

---

### 4. Get URL Statistics

Get detailed statistics for a specific shortened URL.

**Endpoint**: `GET /api/urls/{short_code}/stats`

**Parameters**:
- `short_code` (path) - The short code or custom alias

**Response** (200 OK):
```json
{
  "short_code": "aB3xY9",
  "original_url": "https://www.example.com",
  "created_at": "2024-01-01T12:00:00",
  "click_count": 42,
  "last_accessed_at": "2024-01-15T10:30:00",
  "expires_at": null,
  "is_expired": false
}
```

**Error Responses**:

- **404 Not Found** - Short code doesn't exist
  ```json
  {
    "detail": "Short URL 'abc123' not found"
  }
  ```

**cURL Example**:
```bash
curl "http://localhost:8000/api/urls/aB3xY9/stats"
```

---

### 5. Update URL

Update the destination URL or expiration date.

**Endpoint**: `PUT /api/urls/{short_code}`

**Parameters**:
- `short_code` (path) - The short code or custom alias

**Request Body**:
```json
{
  "original_url": "https://www.newdestination.com",  // Optional
  "expires_at": "2025-12-31T23:59:59"  // Optional
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "short_code": "aB3xY9",
  "original_url": "https://www.newdestination.com",
  "custom_alias": "my-link",
  "created_at": "2024-01-01T12:00:00",
  "expires_at": "2025-12-31T23:59:59",
  "click_count": 42,
  "last_accessed_at": "2024-01-15T10:30:00",
  "short_url": "http://localhost:8000/aB3xY9"
}
```

**Error Responses**:

- **404 Not Found** - Short code doesn't exist
- **400 Bad Request** - Invalid URL format

**cURL Example**:
```bash
curl -X PUT "http://localhost:8000/api/urls/aB3xY9" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://www.newdestination.com"
  }'
```

---

### 6. Delete URL

Permanently delete a shortened URL.

**Endpoint**: `DELETE /api/urls/{short_code}`

**Parameters**:
- `short_code` (path) - The short code or custom alias

**Response** (204 No Content):
- Empty response body

**Error Responses**:

- **404 Not Found** - Short code doesn't exist
  ```json
  {
    "detail": "Short URL 'abc123' not found"
  }
  ```

**cURL Example**:
```bash
curl -X DELETE "http://localhost:8000/api/urls/aB3xY9"
```

---

### 7. Get Summary Statistics

Get overall service statistics.

**Endpoint**: `GET /api/stats`

**Query Parameters**:
- `user_id` (string, optional) - Filter by user ID

**Response** (200 OK):
```json
{
  "total_urls": 150,
  "base_url": "http://localhost:8000",
  "cache": {
    "size": 45,
    "max_size": 1000,
    "hits": 1250,
    "misses": 350,
    "hit_rate": 78.13,
    "total_requests": 1600
  }
}
```

**cURL Example**:
```bash
curl "http://localhost:8000/api/stats"
```

---

### 8. Health Check

Check if the service is running.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "URL Shortener",
  "version": "1.0.0"
}
```

**cURL Example**:
```bash
curl "http://localhost:8000/health"
```

---

## Data Models

### URLCreate

```json
{
  "original_url": "string (required, max 2048 chars)",
  "custom_alias": "string (optional, 4-20 chars, alphanumeric + hyphens/underscores)",
  "expires_at": "datetime (optional, ISO 8601 format)",
  "user_id": "string (optional)"
}
```

### URLUpdate

```json
{
  "original_url": "string (optional, max 2048 chars)",
  "expires_at": "datetime (optional, ISO 8601 format)"
}
```

### URLResponse

```json
{
  "id": "integer",
  "short_code": "string",
  "original_url": "string",
  "custom_alias": "string or null",
  "created_at": "datetime",
  "expires_at": "datetime or null",
  "click_count": "integer",
  "last_accessed_at": "datetime or null",
  "short_url": "string"
}
```

### URLStats

```json
{
  "short_code": "string",
  "original_url": "string",
  "created_at": "datetime",
  "click_count": "integer",
  "last_accessed_at": "datetime or null",
  "expires_at": "datetime or null",
  "is_expired": "boolean"
}
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Resource deleted successfully |
| 307 | Temporary Redirect - Redirecting to original URL |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists |
| 410 | Gone - Resource has expired |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

---

## Custom Alias Rules

1. **Length**: 4-20 characters
2. **Characters**: Letters (a-z, A-Z), numbers (0-9), hyphens (-), underscores (_)
3. **Reserved**: Cannot use: api, admin, health, docs, redoc, openapi, static, assets
4. **Uniqueness**: Must be unique across all URLs

**Valid Examples**:
- `my-link`
- `github_profile`
- `URL2024`
- `test_link_1`

**Invalid Examples**:
- `my link` (contains space)
- `my.link` (contains dot)
- `api` (reserved keyword)
- `abc` (too short)

---

## URL Validation Rules

1. **Scheme**: Must start with `http://` or `https://` (auto-added if missing)
2. **Length**: Maximum 2048 characters
3. **Format**: Must be a valid URL according to RFC 3986
4. **Whitespace**: Leading/trailing whitespace is automatically stripped

---

## Pagination

For list endpoints, use `limit` and `offset` parameters:

```bash
# Get first 10 URLs
curl "http://localhost:8000/api/urls?limit=10&offset=0"

# Get next 10 URLs
curl "http://localhost:8000/api/urls?limit=10&offset=10"

# Get URLs 20-30
curl "http://localhost:8000/api/urls?limit=10&offset=20"
```

---

## Interactive Documentation

Visit these URLs when the service is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

These provide interactive API documentation where you can test endpoints directly from your browser.

---

## Examples

### Complete Workflow Example

```bash
# 1. Create shortened URL
curl -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://www.github.com/NehaKotwal"}'

# Response: {"short_code": "aB3xY9", ...}

# 2. Access shortened URL (redirects)
curl -L "http://localhost:8000/aB3xY9"

# 3. Get statistics
curl "http://localhost:8000/api/urls/aB3xY9/stats"

# 4. Update destination
curl -X PUT "http://localhost:8000/api/urls/aB3xY9" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://www.github.com/NehaKotwal/UrlShortner"}'

# 5. Delete URL
curl -X DELETE "http://localhost:8000/api/urls/aB3xY9"
```

---

## SDKs and Client Libraries

Currently, no official SDKs are available. You can use standard HTTP clients:

### Python
```python
import requests

# Shorten URL
response = requests.post(
    "http://localhost:8000/shorten",
    json={"original_url": "https://www.example.com"}
)
data = response.json()
print(f"Short URL: {data['short_url']}")
```

### JavaScript
```javascript
// Shorten URL
fetch('http://localhost:8000/shorten', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({original_url: 'https://www.example.com'})
})
.then(res => res.json())
.then(data => console.log('Short URL:', data.short_url));
```

### cURL
```bash
curl -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://www.example.com"}'
```

---

For more information, see the [README.md](../README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
