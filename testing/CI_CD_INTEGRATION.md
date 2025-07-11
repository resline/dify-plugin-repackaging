# CI/CD Integration for Performance and Security Testing

## Overview

This document outlines the integration of performance and security testing into the CI/CD pipeline for the Dify Plugin Repackaging application.

## GitHub Actions Workflows

### 1. Performance Testing Workflow

```yaml
# .github/workflows/performance-tests.yml
name: Performance Tests

on:
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:
    inputs:
      test_type:
        description: 'Type of performance test'
        required: true
        default: 'smoke'
        type: choice
        options:
          - smoke
          - load
          - stress
          - endurance

jobs:
  performance-test:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install locust k6 artillery pytest-benchmark
        pip install -r requirements-test.txt
    
    - name: Start application stack
      run: |
        docker-compose -f docker-compose.test.yml up -d
        ./scripts/wait-for-healthy.sh
    
    - name: Run smoke tests
      if: github.event.inputs.test_type == 'smoke' || github.event_name == 'pull_request'
      run: |
        locust -f testing/performance-tests/locustfile.py \
          --headless \
          --users 10 \
          --spawn-rate 2 \
          --run-time 5m \
          --host http://localhost \
          --html performance-report.html \
          --csv performance-metrics
    
    - name: Run load tests
      if: github.event.inputs.test_type == 'load'
      run: |
        locust -f testing/performance-tests/locustfile.py \
          --headless \
          --users 100 \
          --spawn-rate 5 \
          --run-time 30m \
          --host http://localhost \
          --html performance-report.html \
          --csv performance-metrics
    
    - name: Analyze performance results
      run: |
        python scripts/analyze_performance.py \
          --metrics performance-metrics_stats.csv \
          --thresholds testing/performance-thresholds.json
    
    - name: Upload performance artifacts
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: performance-results
        path: |
          performance-report.html
          performance-metrics*.csv
          performance-analysis.json
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const analysis = JSON.parse(fs.readFileSync('performance-analysis.json'));
          
          const comment = `## Performance Test Results
          
          **Summary**: ${analysis.passed ? '✅ Passed' : '❌ Failed'}
          
          ### Key Metrics:
          - **Average Response Time**: ${analysis.avg_response_time}ms
          - **95th Percentile**: ${analysis.p95_response_time}ms
          - **Error Rate**: ${analysis.error_rate}%
          - **Throughput**: ${analysis.throughput} req/s
          
          ### SLA Compliance:
          ${analysis.sla_violations.length === 0 ? '✅ All SLAs met' : '❌ SLA Violations:'}
          ${analysis.sla_violations.map(v => `- ${v}`).join('\n')}
          
          [View detailed report](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})`;
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

### 2. Security Testing Workflow

```yaml
# .github/workflows/security-tests.yml
name: Security Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 3 * * 1'  # Weekly on Monday at 3 AM

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH,MEDIUM'
    
    - name: Upload Trivy results to GitHub Security
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
    
    - name: Run Bandit security linter
      run: |
        pip install bandit
        bandit -r dify-plugin-repackaging-web/backend/app -f json -o bandit-results.json
    
    - name: Run Safety check
      run: |
        pip install safety
        safety check --json --output safety-results.json
    
    - name: Run OWASP ZAP scan
      run: |
        docker run -t owasp/zap2docker-stable zap-baseline.py \
          -t http://localhost \
          -r zap-report.html \
          -J zap-report.json
    
    - name: Run custom security tests
      run: |
        docker-compose -f docker-compose.test.yml up -d
        ./scripts/wait-for-healthy.sh
        python testing/security-tests/security_test_suite.py
    
    - name: Analyze security results
      run: |
        python scripts/analyze_security.py \
          --trivy trivy-results.sarif \
          --bandit bandit-results.json \
          --safety safety-results.json \
          --zap zap-report.json \
          --custom security_report_*.json
    
    - name: Upload security artifacts
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-results
        path: |
          *-results.*
          *-report.*
          security-analysis.json
    
    - name: Create security issue if critical
      if: failure()
      uses: actions/github-script@v6
      with:
        script: |
          const analysis = require('./security-analysis.json');
          
          if (analysis.critical_count > 0) {
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `🚨 Critical Security Vulnerabilities Found`,
              body: `Critical security vulnerabilities detected in build ${context.sha}:
              
              ${analysis.critical_vulnerabilities.map(v => 
                `- **${v.title}**: ${v.description}`
              ).join('\n')}
              
              Please address these immediately.`,
              labels: ['security', 'critical']
            });
          }
```

### 3. Continuous Monitoring Workflow

```yaml
# .github/workflows/continuous-monitoring.yml
name: Continuous Performance & Security Monitoring

on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run synthetic monitoring
      run: |
        # Run synthetic tests against production
        python scripts/synthetic_monitor.py \
          --target ${{ secrets.PRODUCTION_URL }} \
          --tests testing/synthetic-tests/
    
    - name: Check security headers
      run: |
        python scripts/security_headers_check.py \
          --url ${{ secrets.PRODUCTION_URL }}
    
    - name: Performance baseline check
      run: |
        python scripts/performance_baseline.py \
          --url ${{ secrets.PRODUCTION_URL }} \
          --baseline testing/performance-baseline.json
    
    - name: Send alerts if needed
      if: failure()
      run: |
        python scripts/send_alerts.py \
          --webhook ${{ secrets.SLACK_WEBHOOK }} \
          --results monitoring-results.json
```

## Docker Compose for Testing

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  backend-test:
    build: 
      context: ./dify-plugin-repackaging-web/backend
      dockerfile: Dockerfile.test
    environment:
      - TESTING=true
      - REDIS_URL=redis://redis-test:6379/0
      - LOG_LEVEL=DEBUG
    depends_on:
      - redis-test
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis-test:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  worker-test:
    build: 
      context: ./dify-plugin-repackaging-web/backend
      dockerfile: Dockerfile.test
    command: celery -A app.workers.celery_app worker --loglevel=info
    environment:
      - TESTING=true
      - REDIS_URL=redis://redis-test:6379/0
    depends_on:
      - redis-test

  nginx-test:
    image: nginx:alpine
    volumes:
      - ./nginx.test.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend-test
    ports:
      - "80:80"
```

## Scripts for CI/CD

### 1. Performance Analysis Script

```python
#!/usr/bin/env python3
# scripts/analyze_performance.py

import json
import csv
import argparse
import sys
from typing import Dict, List

def analyze_performance(metrics_file: str, thresholds_file: str) -> Dict:
    """Analyze performance metrics against thresholds"""
    
    # Load thresholds
    with open(thresholds_file, 'r') as f:
        thresholds = json.load(f)
    
    # Load metrics
    metrics = {}
    with open(metrics_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Name'] != 'Aggregated':
                metrics[row['Name']] = {
                    'avg_response_time': float(row['Average Response Time']),
                    'p95_response_time': float(row['95%']),
                    'error_rate': float(row['Failure Count']) / float(row['Request Count']) * 100 
                        if float(row['Request Count']) > 0 else 0,
                    'throughput': float(row['Requests/s'])
                }
    
    # Check against thresholds
    violations = []
    for endpoint, endpoint_metrics in metrics.items():
        endpoint_thresholds = thresholds.get(endpoint, thresholds.get('default', {}))
        
        for metric, value in endpoint_metrics.items():
            threshold = endpoint_thresholds.get(metric)
            if threshold and value > threshold:
                violations.append(
                    f"{endpoint}: {metric} = {value:.2f} (threshold: {threshold})"
                )
    
    # Calculate overall metrics
    total_requests = sum(float(m.get('Request Count', 0)) for m in metrics.values())
    total_failures = sum(float(m.get('Failure Count', 0)) for m in metrics.values())
    
    analysis = {
        'passed': len(violations) == 0,
        'avg_response_time': sum(m['avg_response_time'] for m in metrics.values()) / len(metrics),
        'p95_response_time': max(m['p95_response_time'] for m in metrics.values()),
        'error_rate': (total_failures / total_requests * 100) if total_requests > 0 else 0,
        'throughput': sum(m['throughput'] for m in metrics.values()),
        'sla_violations': violations,
        'endpoint_metrics': metrics
    }
    
    # Save analysis
    with open('performance-analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    return analysis

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--metrics', required=True)
    parser.add_argument('--thresholds', required=True)
    args = parser.parse_args()
    
    analysis = analyze_performance(args.metrics, args.thresholds)
    
    if not analysis['passed']:
        print("Performance test failed!")
        print("SLA Violations:")
        for violation in analysis['sla_violations']:
            print(f"  - {violation}")
        sys.exit(1)
    else:
        print("Performance test passed!")
```

### 2. Security Analysis Script

```python
#!/usr/bin/env python3
# scripts/analyze_security.py

import json
import argparse
import sys
from typing import Dict, List

def analyze_security_results(**kwargs) -> Dict:
    """Analyze results from multiple security tools"""
    
    vulnerabilities = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }
    
    # Process Trivy results
    if kwargs.get('trivy'):
        with open(kwargs['trivy'], 'r') as f:
            trivy_data = json.load(f)
            # Process SARIF format
            for run in trivy_data.get('runs', []):
                for result in run.get('results', []):
                    severity = result.get('level', 'warning')
                    if severity == 'error':
                        severity = 'critical'
                    vulnerabilities[severity].append({
                        'source': 'Trivy',
                        'title': result.get('ruleId'),
                        'description': result.get('message', {}).get('text', '')
                    })
    
    # Process custom security test results
    if kwargs.get('custom'):
        import glob
        for custom_file in glob.glob(kwargs['custom']):
            with open(custom_file, 'r') as f:
                custom_data = json.load(f)
                for vuln in custom_data.get('vulnerabilities', []):
                    vulnerabilities[vuln['severity']].append({
                        'source': 'Custom Tests',
                        'title': vuln['category'],
                        'description': vuln['description']
                    })
    
    analysis = {
        'critical_count': len(vulnerabilities['critical']),
        'high_count': len(vulnerabilities['high']),
        'medium_count': len(vulnerabilities['medium']),
        'low_count': len(vulnerabilities['low']),
        'total_count': sum(len(v) for v in vulnerabilities.values()),
        'critical_vulnerabilities': vulnerabilities['critical'],
        'all_vulnerabilities': vulnerabilities
    }
    
    # Save analysis
    with open('security-analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    return analysis

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trivy')
    parser.add_argument('--bandit')
    parser.add_argument('--safety')
    parser.add_argument('--zap')
    parser.add_argument('--custom')
    args = parser.parse_args()
    
    analysis = analyze_security_results(**vars(args))
    
    if analysis['critical_count'] > 0:
        print(f"Critical security vulnerabilities found: {analysis['critical_count']}")
        sys.exit(1)
    elif analysis['high_count'] > 0:
        print(f"High security vulnerabilities found: {analysis['high_count']}")
        sys.exit(1)
    else:
        print(f"Security scan completed. Total issues: {analysis['total_count']}")
```

## Monitoring and Alerting

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Dify Plugin Repackaging - Performance & Security",
    "panels": [
      {
        "title": "Response Time Trends",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~'5..'}[5m])"
          }
        ]
      },
      {
        "title": "Security Events",
        "targets": [
          {
            "expr": "security_events_total"
          }
        ]
      }
    ]
  }
}
```

### Alert Rules

```yaml
# prometheus-alerts.yml
groups:
  - name: performance
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 5
        for: 5m
        annotations:
          summary: "High response time detected"
          
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate above 5%"
  
  - name: security
    rules:
      - alert: SuspiciousActivity
        expr: rate(security_events_total[5m]) > 10
        for: 1m
        annotations:
          summary: "Suspicious activity detected"
```

## Best Practices

1. **Run smoke tests on every PR** - Quick validation
2. **Run full test suite nightly** - Comprehensive validation
3. **Monitor production continuously** - Real-world performance
4. **Track trends over time** - Identify degradation
5. **Automate security patching** - Stay current
6. **Regular penetration testing** - External validation
7. **Performance budgets** - Prevent regression
8. **Security training** - Team awareness