# Debugging manifest.json Issue

## Step 1: Check if file exists in container
```bash
docker exec lims-frontend ls -la /usr/share/nginx/html/ | grep manifest
```

## Step 2: Check what nginx is actually serving
```bash
curl -v http://localhost:3000/manifest.json 2>&1 | head -30
```

## Step 3: Check nginx error logs
```bash
docker exec lims-frontend cat /var/log/nginx/error.log | tail -20
```

## Step 4: Check nginx access logs
```bash
docker exec lims-frontend cat /var/log/nginx/access.log | grep manifest
```

## Step 5: Check manifest-specific log
```bash
docker exec lims-frontend cat /var/log/nginx/manifest.log
```

## Step 6: Test file directly in container
```bash
docker exec lims-frontend cat /usr/share/nginx/html/manifest.json
```

## Step 7: Check nginx config is loaded
```bash
docker exec lims-frontend nginx -t
docker exec lims-frontend cat /etc/nginx/conf.d/default.conf | grep -A 5 manifest
```

## Step 8: If file missing, copy it
```bash
docker cp frontend/build/manifest.json lims-frontend:/usr/share/nginx/html/manifest.json
docker exec lims-frontend nginx -s reload
```

## Step 9: Check browser console
Open browser dev tools → Network tab → Look for manifest.json request → Check Response

