# Dify Plugin Repackaging - Testing Documentation

This directory contains comprehensive testing plans, tools, and configurations for performance and security testing of the Dify Plugin Repackaging application.

## Directory Structure

```
testing/
├── README.md                      # This file
├── PERFORMANCE_TESTING_PLAN.md    # Detailed performance testing strategy
├── SECURITY_TESTING_PLAN.md       # Comprehensive security testing approach
├── CI_CD_INTEGRATION.md          # CI/CD pipeline integration guide
├── performance-thresholds.json    # Performance SLA thresholds
├── performance-tests/
│   └── locustfile.py             # Locust load testing configuration
└── security-tests/
    └── security_test_suite.py    # Automated security test suite
```

## Quick Start

### Running Performance Tests

1. **Install Dependencies**
   ```bash
   pip install locust k6 artillery pytest-benchmark
   ```

2. **Run Smoke Tests** (Quick validation)
   ```bash
   locust -f performance-tests/locustfile.py \
     --headless \
     --users 10 \
     --spawn-rate 2 \
     --run-time 5m \
     --host http://localhost
   ```

3. **Run Load Tests** (Production-like load)
   ```bash
   locust -f performance-tests/locustfile.py \
     --headless \
     --users 100 \
     --spawn-rate 5 \
     --run-time 30m \
     --host http://localhost
   ```

4. **View Results**
   - Open Locust web UI: `locust -f performance-tests/locustfile.py`
   - Navigate to http://localhost:8089

### Running Security Tests

1. **Install Dependencies**
   ```bash
   pip install aiohttp requests websockets
   ```

2. **Run Security Test Suite**
   ```bash
   python security-tests/security_test_suite.py
   ```

3. **Run Specific Security Scans**
   ```bash
   # Dependency scanning
   pip-audit
   safety check
   
   # Static analysis
   bandit -r ../dify-plugin-repackaging-web/backend/app/
   
   # Container scanning
   trivy image dify-plugin-repackaging:latest
   ```

## Key Testing Areas

### Performance Testing

1. **Load Testing Scenarios**
   - Normal production load (100 concurrent users)
   - Peak hour load (500 concurrent users)
   - File size variations (1MB to 100MB)

2. **Critical Metrics**
   - Response time (P50, P95, P99)
   - Throughput (requests/second)
   - Error rate
   - Resource utilization

3. **Performance SLAs**
   - File upload < 10MB: 95th percentile < 2s
   - File download: 95th percentile < 1s
   - API responses: 95th percentile < 500ms
   - Error rate: < 1%

### Security Testing

1. **OWASP Top 10 Coverage**
   - Injection attacks (SQL, Command, Path)
   - Broken authentication
   - Sensitive data exposure
   - XXE/XML attacks
   - Broken access control
   - Security misconfiguration
   - XSS attacks
   - Insecure deserialization
   - Vulnerable components
   - Insufficient logging

2. **Application-Specific Tests**
   - File upload security
   - Path traversal prevention
   - WebSocket security
   - Rate limiting effectiveness
   - CORS configuration

3. **Security Tools**
   - OWASP ZAP
   - Burp Suite
   - Trivy (container scanning)
   - Bandit (Python SAST)
   - Safety (dependency scanning)

## CI/CD Integration

### GitHub Actions

1. **On Pull Request**
   - Smoke performance tests
   - Security linting
   - Dependency scanning

2. **On Main Branch**
   - Full performance test suite
   - Comprehensive security scan
   - OWASP ZAP baseline

3. **Scheduled (Daily)**
   - Endurance testing
   - Dependency updates check
   - Production monitoring

### Performance Gates

- PR must not degrade performance by > 10%
- All SLAs must be met
- No new high/critical vulnerabilities

### Security Gates

- No critical vulnerabilities
- No high vulnerabilities in dependencies
- Security headers present
- Rate limiting functional

## Test Data Requirements

### Performance Testing
- Sample .difypkg files (1MB, 10MB, 50MB, 100MB)
- Marketplace plugin metadata
- Various platform configurations

### Security Testing
- Malicious file samples
- Injection payloads
- Fuzzing dictionaries

## Monitoring & Reporting

### Performance Metrics
- Grafana dashboards
- Prometheus metrics
- Custom performance reports

### Security Reporting
- Vulnerability reports (JSON/HTML)
- SARIF format for GitHub Security
- Email alerts for critical findings

## Best Practices

1. **Test Early and Often**
   - Run tests in development
   - Automate in CI/CD
   - Monitor production

2. **Realistic Test Data**
   - Use production-like file sizes
   - Test with actual plugin packages
   - Simulate real user behavior

3. **Progressive Testing**
   - Start with smoke tests
   - Progress to load tests
   - Perform stress tests periodically

4. **Security-First Approach**
   - Security tests on every commit
   - Regular dependency updates
   - Quarterly penetration testing

5. **Continuous Improvement**
   - Track performance trends
   - Update thresholds based on data
   - Regular security training

## Troubleshooting

### Common Issues

1. **Performance Test Failures**
   - Check resource limits
   - Verify test data availability
   - Review application logs

2. **Security Test False Positives**
   - Validate findings manually
   - Update test configurations
   - Document exceptions

3. **CI/CD Pipeline Issues**
   - Check service health
   - Verify credentials
   - Review timeout settings

## Contributing

When adding new tests:
1. Document the test purpose
2. Add to appropriate test suite
3. Update CI/CD configuration
4. Document any new dependencies
5. Update threshold configurations

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Performance Testing Best Practices](https://www.perfmatrix.com/performance-testing-best-practices/)
- [Security Testing Methodology](https://www.sans.org/cyber-security-courses/)