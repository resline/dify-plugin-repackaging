# REMEDIATION CHECKLIST - Command Injection Fixes
## dify-plugin-repackaging-web

**Deadline:** 48 godzin od identyfikacji
**Assigned to:** Backend Team + Security Team
**Priority:** P0 - CRITICAL

---

## PHASE 1: HOTFIX (0-24h) - KRYTYCZNE

### Backend Python - Input Validation

- [ ] **Task 1.1:** Dodaj walidację parametru `platform`
  - **File:** `/root/repo/dify-plugin-repackaging-web/backend/app/models/task.py`
  - **Action:** Dodaj `@validator` dla whitelist platform values
  - **Est. time:** 30 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.2:** Dodaj walidację parametru `suffix`
  - **File:** `/root/repo/dify-plugin-repackaging-web/backend/app/models/task.py`
  - **Action:** Regex validation `^[a-zA-Z0-9_-]+$`
  - **Est. time:** 30 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.3:** Dodaj sanityzację filename w upload endpoint
  - **File:** `/root/repo/dify-plugin-repackaging-web/backend/app/api/v1/endpoints/tasks.py`
  - **Action:** Implement `sanitize_filename()` function
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Shell Script - Variable Quoting

- [ ] **Task 1.4:** Napraw cytowanie w getopts
  - **File:** `/root/repo/plugin_repackaging.sh`
  - **Lines:** 172-177
  - **Action:** Dodaj regex validation przed assignment
  - **Est. time:** 30 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.5:** Napraw cytowanie w realpath
  - **File:** `/root/repo/plugin_repackaging.sh`
  - **Lines:** 95
  - **Action:** Change to `"$(realpath "$2")"`
  - **Est. time:** 15 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.6:** Napraw cytowanie w unzip command
  - **File:** `/root/repo/plugin_repackaging.sh`
  - **Lines:** 105
  - **Action:** Quote all variables
  - **Est. time:** 15 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.7:** Napraw cytowanie w pip download
  - **File:** `/root/repo/plugin_repackaging.sh`
  - **Lines:** 113
  - **Action:** Use bash array for arguments
  - **Est. time:** 30 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Testing

- [ ] **Task 1.8:** Unit tests dla validation
  - **Files:** Create test files
  - **Action:** Test all validation functions
  - **Est. time:** 2 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.9:** Security testing - injection attempts
  - **Action:** Test wszystkie PoC payloads
  - **Est. time:** 2 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Deployment

- [ ] **Task 1.10:** Code review
  - **Reviewers:** Security Team + Senior Dev
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.11:** Deploy to staging
  - **Action:** Test all endpoints
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 1.12:** Production deployment
  - **Action:** Hotfix deployment
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

---

## PHASE 2: HARDENING (24-72h) - WYSOKIE

### Monitoring & Logging

- [ ] **Task 2.1:** Dodaj security logging
  - **File:** `/root/repo/dify-plugin-repackaging-web/backend/app/services/repackage.py`
  - **Action:** Log wszystkie parametry przed execution
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 2.2:** Alert na injection attempts
  - **Action:** Detect podejrzane znaki w parametrach
  - **Est. time:** 2 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Content Validation

- [ ] **Task 2.3:** Walidacja .difypkg content
  - **File:** Create new validator module
  - **Action:** Validate ZIP structure i file names
  - **Est. time:** 3 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 2.4:** Path traversal protection in ZIP
  - **Action:** Block `..` and absolute paths in ZIP
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Rate Limiting

- [ ] **Task 2.5:** Zmniejsz rate limits
  - **File:** `/root/repo/dify-plugin-repackaging-web/backend/app/core/config.py`
  - **Action:** Change from 30 to 10 per minute
  - **Est. time:** 15 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

---

## PHASE 3: DEFENSE IN DEPTH (1-2 tygodnie) - ŚREDNIE

### Sandboxing

- [ ] **Task 3.1:** Evaluate sandboxing options
  - **Options:** firejail, bubblewrap, gVisor
  - **Est. time:** 4 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 3.2:** Implement sandboxing
  - **File:** `/root/repo/dify-plugin-repackaging-web/backend/app/services/repackage.py`
  - **Est. time:** 8 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Container Security

- [ ] **Task 3.3:** Run as non-root user
  - **File:** Dockerfile
  - **Action:** Add USER directive
  - **Est. time:** 1 hr
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 3.4:** Remove unnecessary tools
  - **File:** Dockerfile
  - **Action:** Remove curl, wget if not needed
  - **Est. time:** 30 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 3.5:** Read-only filesystem
  - **File:** docker-compose.yml
  - **Action:** Mount /app/scripts as read-only
  - **Est. time:** 30 min
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

### Security Testing

- [ ] **Task 3.6:** Automated security scans
  - **Tools:** Bandit, Safety, Semgrep
  - **Est. time:** 4 hrs
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

- [ ] **Task 3.7:** External penetration testing
  - **Vendor:** TBD
  - **Est. time:** 1 week
  - **Assignee:** ___________
  - **Status:** [ ] Todo [ ] In Progress [ ] Done

---

## VERIFICATION TESTS

### Test Case 1: Platform Injection
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg" \
  -F "platform=x86_64; whoami" \
  -F "suffix=offline"

Expected: HTTP 400 Bad Request
Actual: ___________
Status: [ ] Pass [ ] Fail
```

### Test Case 2: Suffix Injection
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg" \
  -F "platform=manylinux2014_x86_64" \
  -F "suffix=test; rm -rf /"

Expected: HTTP 400 Bad Request
Actual: ___________
Status: [ ] Pass [ ] Fail
```

### Test Case 3: Path Traversal
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg;filename=../../../etc/passwd" \
  -F "platform=" \
  -F "suffix=offline"

Expected: Filename sanitized, no path traversal
Actual: ___________
Status: [ ] Pass [ ] Fail
```

### Test Case 4: Valid Request Still Works
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg" \
  -F "platform=manylinux2014_x86_64" \
  -F "suffix=offline"

Expected: HTTP 200 OK, task created
Actual: ___________
Status: [ ] Pass [ ] Fail
```

---

## DOCUMENTATION

- [ ] **Task D.1:** Update security documentation
  - **File:** SECURITY.md
  - **Est. time:** 2 hrs

- [ ] **Task D.2:** Update API documentation
  - **File:** OpenAPI spec
  - **Est. time:** 1 hr

- [ ] **Task D.3:** Create incident report
  - **Audience:** Management
  - **Est. time:** 2 hrs

- [ ] **Task D.4:** Post-mortem meeting
  - **Attendees:** Dev + Security teams
  - **Est. time:** 1 hr

---

## COMMUNICATION

- [ ] **Notify stakeholders**
  - [ ] Engineering Manager
  - [ ] Product Manager
  - [ ] Security Team
  - [ ] DevOps Team

- [ ] **Create incident ticket**
  - **Severity:** P0
  - **Status:** ___________

- [ ] **Schedule daily standups**
  - **Time:** 09:00 daily
  - **Duration:** Until resolved

---

## COMPLETION CRITERIA

All tasks in PHASE 1 must be completed within 24 hours.
All verification tests must pass.
No regressions in functionality.
Security team sign-off required.

---

## SIGN-OFF

**Phase 1 Completed:** __________ (Date/Time)
**Signed by:** __________ (Dev Lead)
**Verified by:** __________ (Security Lead)

**Phase 2 Completed:** __________ (Date/Time)
**Signed by:** __________ (Dev Lead)
**Verified by:** __________ (Security Lead)

**Phase 3 Completed:** __________ (Date/Time)
**Signed by:** __________ (Dev Lead)
**Verified by:** __________ (Security Lead)

---

**EMERGENCY CONTACTS:**
- Security Team: security@company.com
- On-call Engineer: oncall@company.com
- Incident Commander: ___________
