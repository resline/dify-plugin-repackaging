# Security Quickstart Guide

Quick reference for security features in Dify Plugin Repackaging infrastructure.

## TL;DR - What Was Fixed

| Issue | Fix | Benefit |
|-------|-----|---------|
| Running as root | App runs as `appuser` (UID 1000) | Limits damage if compromised |
| No security headers | 6 headers added to nginx | Protects against XSS, clickjacking, MITM |
| No rate limiting | 3 zones: API (10/s), Upload (2/s), WS (5/s) | Stops DDoS and brute force |
| No checksum check | SHA256 verification on download | Ensures binary integrity |

## Quick Build & Test

```bash
# 1. Build with security fixes
cd /root/repo/dify-plugin-repackaging-web
docker build -f Dockerfile.all-in-one -t dify-aio:secure .

# 2. Run container
docker run -d --name dify-aio -p 80:80 \
  -e REDIS_PASSWORD=change_me_in_production \
  dify-aio:secure

# 3. Verify security (wait 10 seconds first)
sleep 10
./verify-security.sh dify-aio localhost 80

# 4. Test manually
curl -I http://localhost/  # Should show security headers
```

## Expected Output

### Build (Checksum Verification)
```
Step 12/20 : RUN mkdir -p /app/scripts && ...
 ---> Running in abc123...
Verifying binary checksums...
dify-plugin-linux-amd64-5g: OK
```

### Security Headers
```bash
$ curl -I http://localhost/

HTTP/1.1 200 OK
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### Rate Limiting
```bash
$ for i in {1..35}; do curl -w "%{http_code}\n" -o /dev/null -s http://localhost/api/health; sleep 0.05; done

200
200
...
200  # First ~30 succeed
429  # Rest are rate limited
429
```

### Non-Root Processes
```bash
$ docker exec dify-aio ps aux | grep -E "appuser.*backend"

appuser    42  1.2  2.3  ...  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Verification Script Output

```bash
$ ./verify-security.sh

==================================================
Security Verification Script
==================================================
Container: dify-plugin-repackaging-aio
Host: localhost:80

==================================================
1. Verifying Non-Root User Execution
==================================================
Checking processes in container...
✓ Backend running as appuser
✓ Celery worker running as appuser
✓ Redis running as appuser
✓ Supervisord running as root (expected)

==================================================
2. Verifying Security Headers
==================================================
Testing security headers...
✓ X-Frame-Options: SAMEORIGIN
✓ X-Content-Type-Options: nosniff
✓ X-XSS-Protection: 1; mode=block
✓ Strict-Transport-Security: max-age=31536000
✓ Referrer-Policy: strict-origin-when-cross-origin
✓ Permissions-Policy: geolocation=()

==================================================
3. Verifying Rate Limiting
==================================================
Testing API rate limiting (sending 35 requests)...
Results:
  - Successful requests: 30
  - Rate limited (429): 5
✓ Rate limiting is working (got 5 rate-limited responses)
...
```

## Common Tasks

### Adjust Rate Limits

Edit `/root/repo/dify-plugin-repackaging-web/Dockerfile.all-in-one`:

```nginx
# Find this section (around line 159-162)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;       # Change 10r/s
limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;     # Change 2r/s
limit_req_zone $binary_remote_addr zone=websocket:10m rate=5r/s;  # Change 5r/s

# Then rebuild
docker build -f Dockerfile.all-in-one -t dify-aio:secure .
```

### Update Binary Checksums

```bash
# When binaries change
cd /root/repo
sha256sum dify-plugin-linux-amd64-5g dify-plugin-linux-arm64-5g \
          dify-plugin-darwin-amd64-5g dify-plugin-darwin-arm64-5g > SHA256SUMS

# Commit
git add SHA256SUMS
git commit -m "Update binary checksums"
```

### Production Deployment

```bash
# Use strong password for Redis
docker run -d \
  --name dify-production \
  -p 80:80 \
  -e REDIS_PASSWORD=$(openssl rand -base64 32) \
  -v /data/redis:/var/lib/redis \
  --restart unless-stopped \
  dify-aio:secure

# For HTTPS, use reverse proxy (nginx/caddy) or update Dockerfile
```

## Files Reference

| File | Purpose |
|------|---------|
| `Dockerfile.all-in-one` | Main security fixes applied here |
| `SECURITY.md` | Detailed documentation (16KB) |
| `SECURITY_CHANGES.md` | Summary of all changes |
| `verify-security.sh` | Automated verification script |
| `../SHA256SUMS` | Binary checksums |

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails at checksum | Regenerate SHA256SUMS with `sha256sum` |
| Too many 429 errors | Increase rate limits in Dockerfile |
| Backend can't start | Check logs: `docker logs dify-aio` |
| Redis auth fails | Set REDIS_PASSWORD env var |
| Can't bind to port 80 | Use `-p 8080:80` or run as privileged |

## Next Steps

1. Read full docs: `cat SECURITY.md`
2. Run verification: `./verify-security.sh`
3. For production: Enable HTTPS and monitoring
4. Adjust rate limits based on your traffic

## Resources

- Full Documentation: `SECURITY.md`
- Change Summary: `SECURITY_CHANGES.md`
- Verification Script: `verify-security.sh`
- OWASP Headers: https://owasp.org/www-project-secure-headers/
