# Security Deployment Checklist
## Dify Plugin Repackaging - Critical Security Fixes

**Target:** Production deployment
**Priority:** P0 - CRITICAL
**Estimated Time:** 4-8 hours
**Required Downtime:** 2-4 hours

---

## Pre-Deployment Checklist

### 1. Backup & Preparation (30 minutes)

- [ ] Backup current production database
- [ ] Backup Redis data (`redis-cli SAVE`)
- [ ] Backup current codebase
  ```bash
  git tag pre-security-fix-$(date +%Y%m%d)
  git push origin --tags
  ```
- [ ] Export environment variables
  ```bash
  env | grep -E 'REDIS|CELERY|MARKETPLACE' > env_backup.txt
  ```
- [ ] List running containers
  ```bash
  docker ps > containers_backup.txt
  ```

### 2. Code Changes Review (1 hour)

#### A. Replace plugin_repackaging.sh

**OLD (VULNERABLE):**
```bash
# Line 105
unzip -o ${PACKAGE_PATH} -d ${CURR_DIR}/${PACKAGE_NAME}
```

**NEW (SECURE):**
```bash
# Add validation before unzip
validate_zip_package() {
    local zip_file=$1
    local extract_dir=$2

    # Check for path traversal
    if unzip -l "$zip_file" | grep -q '\.\.'; then
        echo "ERROR: Path traversal detected"
        return 1
    fi

    # Check uncompressed size (ZIP Bomb)
    local uncompressed_size=$(unzip -l "$zip_file" | tail -1 | awk '{print $1}')
    local max_size=$((500 * 1024 * 1024))  # 500MB
    if [ "$uncompressed_size" -gt "$max_size" ]; then
        echo "ERROR: Archive too large: $uncompressed_size bytes"
        return 1
    fi

    return 0
}

# Use it
validate_zip_package "${PACKAGE_PATH}" "${CURR_DIR}/${PACKAGE_NAME}" || exit 1
unzip -o ${PACKAGE_PATH} -d ${CURR_DIR}/${PACKAGE_NAME}
```

**Files to modify:**
- [ ] `/root/repo/plugin_repackaging.sh`
- [ ] `/root/repo/dify-plugin-repackaging-web/backend/scripts/plugin_repackaging.sh`

#### B. Update requirements.txt handling

**OLD (VULNERABLE):**
```bash
# Line 113
pip download ${PIP_PLATFORM} -r requirements.txt -d ./wheels \
    --index-url ${PIP_MIRROR_URL} --trusted-host mirrors.aliyun.com
```

**NEW (SECURE):**
```bash
# Validate requirements.txt first
validate_requirements() {
    local req_file=$1

    # Block dangerous patterns
    if grep -qE 'git\+|file://|http://|^-e |^--' "$req_file"; then
        echo "ERROR: Dangerous pattern in requirements.txt"
        return 1
    fi

    return 0
}

# Use it
validate_requirements requirements.txt || exit 1

# Use safe pip download (REMOVE --trusted-host!)
pip download ${PIP_PLATFORM:+--platform "$PIP_PLATFORM"} \
    --no-deps \
    --only-binary=:all: \
    --disable-pip-version-check \
    --index-url https://pypi.org/simple/ \
    -r requirements.txt \
    -d ./wheels
```

**Files to modify:**
- [ ] `/root/repo/plugin_repackaging.sh` (line 113)
- [ ] `/root/repo/dify-plugin-repackaging-web/backend/scripts/plugin_repackaging.sh` (line 113)

#### C. Add Python-based safe extraction

**Create new file:** `/root/repo/dify-plugin-repackaging-web/backend/app/utils/zip_security.py`

```python
# Copy from SECURITY_FIXES_REFERENCE.py
from SECURITY_FIXES_REFERENCE import (
    safe_extract,
    validate_requirements_txt,
    validate_platform
)
```

**Files to create:**
- [ ] `/root/repo/dify-plugin-repackaging-web/backend/app/utils/zip_security.py`

#### D. Update tasks.py endpoint

**Add validation in upload endpoint (line 360):**

```python
# tasks.py - around line 360
from app.utils.zip_security import safe_extract, validate_requirements_txt

@router.post("/tasks/upload", response_model=TaskResponse)
async def upload_task(...):
    # ... existing code ...

    # ADD: Validate file header
    file.file.seek(0)
    header = file.file.read(4)
    file.file.seek(0)

    if header != b'PK\x03\x04':
        raise HTTPException(400, "Not a valid ZIP file")

    # ADD: Validate filename
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', file.filename)
    if safe_filename != file.filename:
        raise HTTPException(400, "Invalid characters in filename")

    # ... continue with existing code ...
```

**Files to modify:**
- [ ] `/root/repo/dify-plugin-repackaging-web/backend/app/api/v1/endpoints/tasks.py`

---

### 3. Testing in Staging (2 hours)

#### Unit Tests

- [ ] Test safe_extract with path traversal ZIP
  ```bash
  cd /root/repo/dify-plugin-repackaging-web/backend
  python3 -m pytest tests/test_zip_security.py -v
  ```

- [ ] Test requirements.txt validation
  ```bash
  python3 -m pytest tests/test_requirements_validation.py -v
  ```

#### Integration Tests

- [ ] Upload legitimate .difypkg file
  ```bash
  curl -X POST http://staging:8000/api/v1/tasks/upload \
       -F "file=@legitimate_plugin.difypkg" \
       -F "platform=manylinux2014_x86_64"
  ```

- [ ] Test ZIP Slip protection (should FAIL)
  ```bash
  # Create malicious ZIP
  python3 create_malicious_zip.py --type path-traversal

  # Try to upload (should be rejected)
  curl -X POST http://staging:8000/api/v1/tasks/upload \
       -F "file=@malicious.difypkg"
  # Expected: HTTP 400 with "Path traversal" error
  ```

- [ ] Test ZIP Bomb protection (should FAIL)
  ```bash
  python3 create_malicious_zip.py --type zip-bomb

  curl -X POST http://staging:8000/api/v1/tasks/upload \
       -F "file=@zipbomb.difypkg"
  # Expected: HTTP 400 with "Archive too large" error
  ```

- [ ] Test requirements.txt injection (should FAIL)
  ```bash
  # Create package with malicious requirements.txt
  python3 create_malicious_zip.py --type requirements-injection

  curl -X POST http://staging:8000/api/v1/tasks/upload \
       -F "file=@malicious_req.difypkg"
  # Expected: Repackaging fails with validation error
  ```

**Test Results Log:**
```
[ ] All unit tests passed
[ ] Legitimate upload works
[ ] Path traversal blocked
[ ] ZIP bomb blocked
[ ] Requirements injection blocked
[ ] Performance acceptable (< 2x slower)
```

---

### 4. Production Deployment (1-2 hours)

#### Step 1: Maintenance Mode (5 minutes)

```bash
# Enable maintenance page
docker exec nginx sh -c 'echo "Maintenance in progress" > /usr/share/nginx/html/maintenance.html'
docker exec nginx nginx -s reload

# Stop accepting new tasks
docker exec backend curl -X POST http://localhost:8000/api/v1/maintenance/enable
```

#### Step 2: Wait for Tasks to Complete (10-30 minutes)

```bash
# Monitor active tasks
watch -n 5 'docker exec redis redis-cli KEYS "task:*" | wc -l'

# Wait until all tasks complete or timeout (30 min)
timeout 1800 bash -c 'while [ $(docker exec redis redis-cli KEYS "task:*" | wc -l) -gt 0 ]; do sleep 10; done'
```

#### Step 3: Stop Services (2 minutes)

```bash
cd /root/repo/dify-plugin-repackaging-web

# Stop backend and workers
docker-compose stop backend worker

# Keep Redis and database running
```

#### Step 4: Deploy New Code (5 minutes)

```bash
# Pull latest code
git fetch origin
git checkout security-fixes-branch

# Or apply patches
git apply security-fixes.patch

# Rebuild containers
docker-compose build backend worker

# Verify images built
docker images | grep dify-repackaging
```

#### Step 5: Start Services (2 minutes)

```bash
# Start backend
docker-compose up -d backend

# Wait for health check
timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

# Start workers
docker-compose up -d worker

# Verify all running
docker-compose ps
```

#### Step 6: Smoke Tests (10 minutes)

```bash
# Test 1: Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Test 2: Upload legitimate file
curl -X POST http://localhost:8000/api/v1/tasks/upload \
     -F "file=@test_plugin.difypkg" \
     -F "platform=manylinux2014_x86_64"
# Expected: HTTP 200 with task_id

# Test 3: Monitor task completion
TASK_ID=<from_above>
watch -n 2 "curl http://localhost:8000/api/v1/tasks/$TASK_ID"
# Wait for status: "completed"

# Test 4: Download result
curl -O http://localhost:8000/api/v1/tasks/$TASK_ID/download

# Test 5: Verify result is valid ZIP
unzip -t <downloaded_file>.difypkg
```

#### Step 7: Disable Maintenance Mode (2 minutes)

```bash
# Remove maintenance page
docker exec nginx rm /usr/share/nginx/html/maintenance.html
docker exec nginx nginx -s reload

# Enable task acceptance
docker exec backend curl -X POST http://localhost:8000/api/v1/maintenance/disable
```

---

### 5. Post-Deployment Monitoring (24 hours)

#### Metrics to Watch

- [ ] Error rate (should be < 1%)
  ```bash
  docker logs backend --since 1h | grep ERROR | wc -l
  ```

- [ ] Task success rate (should be > 95%)
  ```bash
  docker exec redis redis-cli KEYS "task:*" | \
    xargs docker exec redis redis-cli MGET | \
    grep -c '"status":"completed"'
  ```

- [ ] Security alerts (should be 0)
  ```bash
  docker logs backend | grep -i "SECURITY:"
  ```

- [ ] Resource usage
  ```bash
  docker stats backend worker
  # CPU should be < 80%, Memory < 90%
  ```

#### Alert Thresholds

Set up alerts for:
- [ ] Error rate > 5% over 5 minutes
- [ ] Task failure rate > 10% over 10 minutes
- [ ] CPU usage > 90% for 5 minutes
- [ ] Disk usage > 85%
- [ ] Any SECURITY: log entries

---

### 6. Rollback Plan (if needed)

**Trigger rollback if:**
- Error rate > 10%
- More than 3 security bypass attempts detected
- Service unavailable for > 5 minutes
- Data corruption detected

**Rollback steps:**

```bash
# 1. Stop services
docker-compose stop backend worker

# 2. Restore previous version
git checkout pre-security-fix-$(date +%Y%m%d)

# 3. Rebuild
docker-compose build backend worker

# 4. Restore data (if needed)
docker exec redis redis-cli FLUSHALL
docker exec redis redis-cli RESTORE <backup_key> <ttl> <serialized_value>

# 5. Start services
docker-compose up -d backend worker

# 6. Notify team
echo "ROLLBACK: Security fixes rolled back due to issues" | \
  mail -s "ALERT: Rollback" team@example.com
```

---

## Post-Deployment Tasks

### Week 1

- [ ] Monitor security logs daily
- [ ] Review error logs for false positives
- [ ] Collect performance metrics
- [ ] User feedback survey

### Week 2

- [ ] Fine-tune security thresholds
- [ ] Optimize validation performance
- [ ] Update documentation
- [ ] Security training for team

### Week 3

- [ ] Penetration testing
- [ ] Load testing with security fixes
- [ ] Review incident response plan
- [ ] Update disaster recovery procedures

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **Developer** | _________ | ______ | _________ |
| **DevOps** | _________ | ______ | _________ |
| **Security** | _________ | ______ | _________ |
| **Product Manager** | _________ | ______ | _________ |

---

## Emergency Contacts

- **Security Team:** security@example.com / +1-XXX-XXX-XXXX
- **DevOps On-Call:** devops@example.com / +1-XXX-XXX-XXXX
- **Product Manager:** pm@example.com / +1-XXX-XXX-XXXX

---

## References

- Full Security Audit: `/root/repo/SECURITY_AUDIT_REPORT.md`
- Executive Summary: `/root/repo/SECURITY_EXECUTIVE_SUMMARY.md`
- Code Reference: `/root/repo/SECURITY_FIXES_REFERENCE.py`
- Test Cases: `/root/repo/testing/security-tests/`

---

**Last Updated:** 2025-12-28
**Next Review:** 2026-01-28
