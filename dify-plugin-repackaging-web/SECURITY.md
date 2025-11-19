# Security Enhancements

This document describes the security improvements implemented in the Dify Plugin Repackaging infrastructure.

## Overview

The following security measures have been implemented to protect the application:

1. Non-root user execution
2. Security headers in nginx
3. Rate limiting for API endpoints
4. Binary checksum verification

## 1. Non-Root User Execution

### Implementation
- Created dedicated user `appuser` with UID 1000
- All application processes (backend, celery, redis) run as `appuser`
- Only supervisord runs as root to manage services and nginx
- Proper file ownership and permissions set for all directories

### Benefits
- Limits attack surface if container is compromised
- Follows principle of least privilege
- Prevents unauthorized system modifications

### Configuration
```dockerfile
# Create non-root user
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -m -s /bin/bash appuser

# Set ownership
RUN chown -R appuser:appuser /app /usr/share/nginx/html
```

## 2. Security Headers

### Implemented Headers

#### X-Frame-Options: SAMEORIGIN
Prevents clickjacking attacks by disallowing the page to be embedded in iframes from different origins.

#### X-Content-Type-Options: nosniff
Prevents MIME-type sniffing, forcing browsers to respect declared content types.

#### X-XSS-Protection: 1; mode=block
Enables browser's XSS filter to block suspected XSS attacks.

#### Strict-Transport-Security: max-age=31536000; includeSubDomains
Forces HTTPS connections for 1 year, including all subdomains.
**Note:** Only effective when site is served over HTTPS.

#### Referrer-Policy: strict-origin-when-cross-origin
Controls referrer information sent with requests.

#### Permissions-Policy: geolocation=(), microphone=(), camera=()
Disables potentially sensitive browser features.

### Configuration
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

## 3. Rate Limiting

### Purpose
Protects against:
- Brute force attacks
- DDoS attacks
- Resource exhaustion
- API abuse

### Configuration

#### API Endpoints (10 req/s)
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api {
    limit_req zone=api burst=20 nodelay;
    limit_req_status 429;
    ...
}
```

#### Upload Endpoints (2 req/s)
```nginx
limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

location /api/upload {
    limit_req zone=upload burst=5 nodelay;
    limit_req_status 429;
    ...
}
```

#### WebSocket Endpoints (5 req/s)
```nginx
limit_req_zone $binary_remote_addr zone=websocket:10m rate=5r/s;

location /ws {
    limit_req zone=websocket burst=10 nodelay;
    limit_req_status 429;
    ...
}
```

### Rate Limit Parameters
- **zone**: Shared memory zone (10MB stores ~160,000 IP addresses)
- **rate**: Base rate (requests per second)
- **burst**: Allows short traffic spikes
- **nodelay**: Processes burst requests immediately (no queuing)
- **limit_req_status 429**: Returns HTTP 429 (Too Many Requests) when limit exceeded

### Adjusting Limits
Edit `/etc/nginx/nginx.conf` in the container or rebuild with modified Dockerfile:

```nginx
# More strict
limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;

# More permissive
limit_req_zone $binary_remote_addr zone=api:10m rate=20r/s;
```

## 4. Binary Checksum Verification

### Purpose
Ensures downloaded binaries haven't been tampered with during download.

### Implementation
```dockerfile
# Download binaries and checksums
wget -q https://github.com/resline/dify-plugin-repackaging/raw/main/dify-plugin-linux-amd64-5g
wget -q https://github.com/resline/dify-plugin-repackaging/raw/main/SHA256SUMS

# Verify checksums
grep "dify-plugin-linux-amd64-5g" SHA256SUMS | sha256sum -c -
```

### SHA256 Checksums
See `/root/repo/SHA256SUMS` for current checksums:

```
5b6235064938e06b8d9e4d6bf8dcdaeb42d960c6a5dec9d9fd3e5f63ca08e700  dify-plugin-linux-amd64-5g
01529c850d8c0de52b82eefb16f8c42b71211e418c04eb370b1093b924c731c1  dify-plugin-linux-arm64-5g
0ae5c2d2e1f901b1a4ff5935aba48083a542067dde4d27f05849e5e0fecdd2e8  dify-plugin-darwin-amd64-5g
f1bee619501e1ed5818a0b1c0dcbd57c3e540b0f78680250604f6e6078977003  dify-plugin-darwin-arm64-5g
```

### Updating Checksums
When updating binaries:

```bash
# Generate new checksums
sha256sum dify-plugin-* > SHA256SUMS

# Commit to repository
git add SHA256SUMS
git commit -m "Update binary checksums"
git push
```

## Verification

### 1. Check User Running Processes

```bash
# Inside container
docker exec -it <container> ps aux

# You should see:
# - supervisord running as root
# - nginx running as root (needs port 80)
# - backend, worker, celery-beat running as appuser
# - redis running as appuser
```

### 2. Test Security Headers

```bash
# Test with curl
curl -I http://localhost:80

# Expected headers:
# X-Frame-Options: SAMEORIGIN
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 3. Test Rate Limiting

```bash
# Test API rate limit (should get 429 after 30 requests in ~2 seconds)
for i in {1..35}; do
  curl -w "%{http_code}\n" -o /dev/null -s http://localhost/api/health
  sleep 0.05
done

# Expected output:
# 200 (first 30 requests)
# 429 (remaining 5 requests)
```

### 4. Verify Checksum

```bash
# During build, you should see:
# Verifying binary checksums...
# dify-plugin-linux-amd64-5g: OK

# If checksum fails, build will abort:
# dify-plugin-linux-amd64-5g: FAILED
# sha256sum: WARNING: 1 computed checksum did NOT match
```

## Production Recommendations

### 1. HTTPS Setup
Enable HTTPS for full security header benefits:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ...
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

### 2. Firewall Rules
Limit access to specific IPs if possible:

```nginx
# In nginx config
location /api/admin {
    allow 10.0.0.0/8;
    deny all;
    ...
}
```

### 3. Regular Updates
- Keep base images updated
- Monitor security advisories for dependencies
- Regularly regenerate and verify checksums

### 4. Monitoring
Set up monitoring for:
- 429 rate limit responses (potential attack)
- Failed authentication attempts
- Unusual traffic patterns

### 5. Additional Headers
Consider adding:

```nginx
# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

# Additional security
add_header X-Permitted-Cross-Domain-Policies "none" always;
add_header Expect-CT "max-age=86400, enforce" always;
```

## Troubleshooting

### Issue: Backend can't write to logs
**Solution:** Check ownership
```bash
docker exec <container> ls -la /var/log/
# Should be owned by appuser:appuser
```

### Issue: Redis can't start
**Solution:** Check Redis directory permissions
```bash
docker exec <container> ls -la /var/lib/redis/
# Should be owned by appuser:appuser
```

### Issue: Rate limiting too strict
**Solution:** Adjust limits in Dockerfile.all-in-one
```nginx
# Increase rate from 10r/s to 20r/s
limit_req_zone $binary_remote_addr zone=api:10m rate=20r/s;
```

### Issue: Checksum verification fails
**Solution:** Regenerate checksums
```bash
# On host machine
sha256sum dify-plugin-linux-amd64-5g
# Update SHA256SUMS file with new checksum
```

## References

- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [Nginx Rate Limiting](https://www.nginx.com/blog/rate-limiting-nginx/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
