#!/bin/bash
echo "=== TESTING LOGIN ==="
echo ""
echo "1. Testing backend health:"
curl -v http://localhost:8000/health
echo ""
echo ""
echo "2. Testing nginx proxy:"
curl -v http://localhost:3000/api/health
echo ""
echo ""
echo "3. Testing login endpoint directly:"
curl -v -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
echo ""
echo ""
echo "4. Testing login via nginx proxy:"
curl -v -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
echo ""
echo ""
echo "5. Check backend logs:"
docker logs lims-backend --tail 20

