# Debugging 404 Errors - Complete Guide

## Common Issues and Fixes

### Issue 1: Route Trailing Slash Mismatch

**Problem:** Routes registered as `/samples/` but frontend calls `/samples` (no trailing slash). With `redirect_slashes=False`, FastAPI doesn't match them.

**Solution:** Changed route definitions from `@router.get("/")` to `@router.get("")` so routes become `/samples` instead of `/samples/`.

**Affected Routes:**
- `/samples` → Fixed
- `/projects` → Fixed
- `/batches` → Fixed
- `/containers` → Fixed
- `/tests` → Fixed

### Issue 2: Empty String Query Parameters

**Problem:** Frontend sends empty strings for optional UUID query parameters (e.g., `status=`, `project_id=`). FastAPI can't parse empty strings as UUIDs.

**Solution:** Changed query parameters from `Optional[UUID]` to `Optional[str]` and added manual UUID parsing with empty string handling:

```python
# Convert empty strings to None and parse UUIDs
project_id_uuid = None
if project_id and project_id.strip():
    try:
        project_id_uuid = UUID(project_id)
    except (ValueError, AttributeError):
        pass
```

**Affected Endpoints:**
- `GET /samples` → Fixed

### Issue 3: Missing API Routers

**Problem:** Frontend calls endpoints that don't exist in the backend.

**Solution:** Created missing routers:
- `/analyses` → Created `backend/app/routers/analyses.py`
- `/units` → Created `backend/app/routers/units.py`

**Fixed Path Mismatches:**
- `/container-types` → Changed frontend to use `/containers/types`

### Issue 4: Response Format Mismatch

**Problem:** API returns paginated response objects (e.g., `{samples: [...], total: ...}`) but frontend expects arrays.

**Solution:** Updated `apiService` to extract arrays from response objects:

```typescript
// Extract the samples array from SampleListResponse
return response.data.samples || response.data;
```

**Affected Endpoints:**
- `GET /samples` → Fixed
- `GET /batches` → Fixed

### Issue 5: Missing Permissions

**Problem:** Endpoints require permissions that don't exist in the database.

**Solution:** Added missing `batch:read` permission to migrations:
- Created migration `0008_add_batch_read_permission.py`
- Added permission to Administrator and Lab Manager roles

**Affected Endpoints:**
- `GET /batches` → Fixed

## Debugging Steps

### Step 1: Check if Backend Routes are Registered

```bash
docker logs lims-backend | grep -A 20 "Registering routers"
```

Should show: "All routers registered"

### Step 2: Test Backend Endpoints Directly (Bypass Nginx)

First, get an auth token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}' | jq -r '.access_token')
```

Then test the endpoints directly on the backend:
```bash
# Test /samples endpoint
curl -v "http://localhost:8000/samples?status=&project_id=" \
  -H "Authorization: Bearer $TOKEN"

# Test /projects endpoint  
curl -v "http://localhost:8000/projects" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** Should return 200 OK with data, or 401 if auth fails, or 403 if permissions fail.

### Step 3: Test Through Nginx Proxy

Test if nginx is forwarding correctly:
```bash
# Test /api/samples through nginx
curl -v "http://localhost:3000/api/samples?status=&project_id=" \
  -H "Authorization: Bearer $TOKEN"

# Test /api/projects through nginx
curl -v "http://localhost:3000/api/projects" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** Should return same as Step 2.

### Step 4: Check Nginx Proxy Configuration

The nginx config has:
```
location /api/ {
    proxy_pass http://backend:8000/;
```

This means:
- Request: `http://localhost:3000/api/samples`
- Nginx strips `/api/` and forwards: `http://backend:8000/samples`

Check nginx logs:
```bash
docker exec lims-frontend cat /var/log/nginx/access.log | tail -10
docker exec lims-frontend cat /var/log/nginx/error.log | tail -10
```

### Step 5: Check Backend Logs for Incoming Requests

Watch backend logs in real-time:
```bash
docker logs -f lims-backend
```

Then trigger the request from the browser. Look for:
- `=== REQUEST: GET /samples ===` or `=== REQUEST: GET /projects ===`
- What status code is returned
- Any error messages

### Step 6: Check Authentication

The endpoints require authentication. Check if:
1. Token is being sent in the request
2. Token is valid
3. User has required permissions

In browser console:
```javascript
console.log('Token:', localStorage.getItem('token'));
```

### Step 7: Check FastAPI Route Registration

Verify the routes are actually registered by checking the OpenAPI docs:
```bash
docker exec lims-backend curl -s http://localhost:8000/openapi.json | jq '.paths | keys' | grep -E '(samples|projects)'
```

## Common Issues:

1. **Backend not restarted** - Routes won't be available until backend restarts
2. **Empty string query params** - Empty strings can't be parsed as UUIDs (FIXED)
3. **Authentication failure** - Some endpoints might return 404 instead of 401
4. **Nginx proxy misconfiguration** - Check if `/api/` is being stripped correctly
5. **Route path mismatch** - Verify route paths match exactly

## Quick Test Commands:

```bash
# 1. Check if backend is running
docker exec lims-backend curl http://localhost:8000/health

# 2. Check if routes are registered
docker exec lims-backend curl http://localhost:8000/openapi.json | jq '.paths | keys'

# 3. Test authentication
docker exec lims-backend curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 4. Test endpoint with auth
TOKEN="your-token-here"
docker exec lims-backend curl http://localhost:8000/samples \
  -H "Authorization: Bearer $TOKEN"
```

## All Fixes Applied

1. **Route Trailing Slashes**: All list endpoints changed from `@router.get("/")` to `@router.get("")`
2. **Empty String Handling**: Query parameters accept strings and convert to UUIDs manually
3. **Missing Routers**: Created `/analyses` and `/units` routers
4. **Response Format**: Frontend extracts arrays from paginated responses
5. **Permissions**: Added `batch:read` permission to migrations

## API Endpoints Summary

### Working Endpoints
- `GET /samples` - List samples with filtering (accepts UUID query params)
- `GET /projects` - List projects
- `GET /batches` - List batches with filtering (requires `batch:read` permission)
- `GET /containers` - List containers
- `GET /tests` - List tests with filtering (requires authentication, scoped by RLS)
- `GET /analyses` - List analyses
- `GET /units` - List units
- `GET /lists/{list_name}/entries` - Get list entries (uses normalized names like `sample_status`)
- `GET /containers/types` - Get container types

### Query Parameter Format
All UUID query parameters must be valid UUIDs. Empty strings are converted to `None` automatically.

### Response Format
List endpoints return paginated responses:
```json
{
  "samples": [...],
  "total": 100,
  "page": 1,
  "size": 10,
  "pages": 10
}
```

The frontend `apiService` extracts the array automatically.
