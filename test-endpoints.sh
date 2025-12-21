#!/bin/bash

# Test script to debug 404 errors
# Usage: ./test-endpoints.sh

echo "=== Testing Backend Endpoints ==="
echo ""

# Step 1: Check backend health
echo "1. Testing backend health..."
HEALTH=$(curl -s http://localhost:8000/health)
echo "   Health check: $HEALTH"
echo ""

# Step 2: Try to get auth token (if credentials are known)
echo "2. Attempting authentication..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' 2>&1)

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
  TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')
  if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "   ✓ Authentication successful"
    echo ""
    
    # Step 3: Test /samples endpoint directly on backend
    echo "3. Testing /samples endpoint on backend (port 8000)..."
    SAMPLES_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:8000/samples?status=&project_id=" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$SAMPLES_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    echo "   HTTP Status: $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
      echo "   ✓ /samples endpoint works on backend"
    else
      echo "   ✗ /samples endpoint failed (Status: $HTTP_CODE)"
      echo "   Response: $(echo "$SAMPLES_RESPONSE" | grep -v HTTP_CODE | head -5)"
    fi
    echo ""
    
    # Step 4: Test /projects endpoint directly on backend
    echo "4. Testing /projects endpoint on backend (port 8000)..."
    PROJECTS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:8000/projects" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$PROJECTS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    echo "   HTTP Status: $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
      echo "   ✓ /projects endpoint works on backend"
    else
      echo "   ✗ /projects endpoint failed (Status: $HTTP_CODE)"
      echo "   Response: $(echo "$PROJECTS_RESPONSE" | grep -v HTTP_CODE | head -5)"
    fi
    echo ""
    
    # Step 5: Test through nginx proxy
    echo "5. Testing /api/samples through nginx (port 3000)..."
    SAMPLES_PROXY_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:3000/api/samples?status=&project_id=" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$SAMPLES_PROXY_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    echo "   HTTP Status: $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
      echo "   ✓ /api/samples endpoint works through nginx"
    else
      echo "   ✗ /api/samples endpoint failed through nginx (Status: $HTTP_CODE)"
      echo "   Response: $(echo "$SAMPLES_PROXY_RESPONSE" | grep -v HTTP_CODE | head -5)"
    fi
    echo ""
    
    # Step 6: Test /api/projects through nginx
    echo "6. Testing /api/projects through nginx (port 3000)..."
    PROJECTS_PROXY_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:3000/api/projects" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$PROJECTS_PROXY_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    echo "   HTTP Status: $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
      echo "   ✓ /api/projects endpoint works through nginx"
    else
      echo "   ✗ /api/projects endpoint failed through nginx (Status: $HTTP_CODE)"
      echo "   Response: $(echo "$PROJECTS_PROXY_RESPONSE" | grep -v HTTP_CODE | head -5)"
    fi
    echo ""
    
  else
    echo "   ✗ No token in response"
    echo "   Response: $LOGIN_RESPONSE"
  fi
else
  echo "   ✗ Authentication failed"
  echo "   Response: $LOGIN_RESPONSE"
  echo ""
  echo "   Note: Update username/password in this script if different"
fi

echo ""
echo "=== Checking Backend Logs ==="
echo "Recent backend requests:"
docker logs lims-backend --tail 20 | grep -E "(REQUEST|RESPONSE)" | tail -10

echo ""
echo "=== Checking Nginx Logs ==="
echo "Recent nginx access logs:"
docker exec lims-frontend tail -10 /var/log/nginx/access.log 2>/dev/null || echo "   (nginx logs not accessible)"

echo ""
echo "=== Test Complete ==="

