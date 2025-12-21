#!/bin/bash
# Debug script for manifest.json issue

echo "=== Step 1: Check if manifest.json exists in container ==="
docker exec lims-frontend ls -la /usr/share/nginx/html/manifest.json 2>&1
echo ""

echo "=== Step 2: Check file contents in container ==="
docker exec lims-frontend cat /usr/share/nginx/html/manifest.json 2>&1 | head -5
echo ""

echo "=== Step 3: Test nginx debug endpoint ==="
curl -s http://localhost:3000/debug-test
echo ""
echo ""

echo "=== Step 4: Test manifest.json endpoint (first 20 lines) ==="
curl -v http://localhost:3000/manifest.json 2>&1 | head -20
echo ""

echo "=== Step 5: Check nginx error log ==="
docker exec lims-frontend tail -10 /var/log/nginx/error.log 2>&1
echo ""

echo "=== Step 6: Check manifest access log ==="
docker exec lims-frontend cat /var/log/nginx/manifest.log 2>&1 | tail -5
echo ""

echo "=== Step 7: Verify nginx config ==="
docker exec lims-frontend nginx -t 2>&1
echo ""

echo "=== Step 8: Show manifest location block from config ==="
docker exec lims-frontend grep -A 5 "location = /manifest.json" /etc/nginx/conf.d/default.conf 2>&1

