"""
Test utilities for service orchestration and integration testing.
"""
import os
import time
import asyncio
import subprocess
import docker
import logging
from typing import Dict, List, Optional, Callable
from tenacity import retry, stop_after_delay, wait_fixed
import httpx
import redis
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """Orchestrate services for integration testing."""
    
    def __init__(self, compose_file: str = "docker-compose.test.yml"):
        self.compose_file = compose_file
        self.project_name = "dify-repack-test"
        self.docker_client = docker.from_env()
    
    def start_services(self, services: Optional[List[str]] = None):
        """Start Docker Compose services."""
        cmd = [
            "docker-compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "up", "-d"
        ]
        
        if services:
            cmd.extend(services)
        
        logger.info(f"Starting services: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    
    def stop_services(self):
        """Stop Docker Compose services."""
        cmd = [
            "docker-compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "down", "-v"
        ]
        
        logger.info("Stopping services")
        subprocess.run(cmd, check=True)
    
    def get_service_logs(self, service_name: str) -> str:
        """Get logs from a specific service."""
        try:
            container = self.docker_client.containers.get(f"{self.project_name}_{service_name}_1")
            return container.logs(tail=100).decode('utf-8')
        except docker.errors.NotFound:
            return f"Container {service_name} not found"
    
    @retry(stop=stop_after_delay(60), wait=wait_fixed(2))
    def wait_for_service(self, service_name: str, health_check: Callable):
        """Wait for a service to be healthy."""
        logger.info(f"Waiting for {service_name} to be healthy...")
        health_check()
        logger.info(f"{service_name} is healthy")
    
    def scale_service(self, service_name: str, replicas: int):
        """Scale a service to specified number of replicas."""
        cmd = [
            "docker-compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "up", "-d",
            "--scale", f"{service_name}={replicas}",
            service_name
        ]
        
        logger.info(f"Scaling {service_name} to {replicas} replicas")
        subprocess.run(cmd, check=True)


class HealthChecks:
    """Health check utilities for services."""
    
    @staticmethod
    def check_redis(url: str = "redis://localhost:6380/0"):
        """Check if Redis is healthy."""
        client = redis.from_url(url)
        client.ping()
        client.close()
    
    @staticmethod
    async def check_backend(url: str = "http://localhost:8000"):
        """Check if backend API is healthy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/health")
            response.raise_for_status()
    
    @staticmethod
    def check_celery_worker(broker_url: str):
        """Check if Celery workers are healthy."""
        from celery import Celery
        app = Celery(broker=broker_url)
        
        i = app.control.inspect()
        stats = i.stats()
        if not stats:
            raise Exception("No Celery workers available")
    
    @staticmethod
    async def check_websocket(url: str = "ws://localhost:8000/ws/test"):
        """Check if WebSocket endpoint is accessible."""
        import websockets
        
        async with websockets.connect(url) as ws:
            await ws.send('{"type": "ping"}')
            response = await ws.recv()
            if not response:
                raise Exception("No WebSocket response")


class TestDataGenerator:
    """Generate test data for integration tests."""
    
    @staticmethod
    def create_mock_plugin_file(path: str, size_mb: int = 1) -> str:
        """Create a mock plugin file."""
        import zipfile
        import tempfile
        
        # Create a temporary directory for plugin contents
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create plugin files
            manifest_content = {
                "name": "test-plugin",
                "version": "1.0.0",
                "author": "test",
                "dependencies": ["requests==2.31.0", "pydantic==2.5.0"]
            }
            
            manifest_path = os.path.join(temp_dir, "manifest.json")
            with open(manifest_path, "w") as f:
                import json
                json.dump(manifest_content, f)
            
            # Create requirements.txt
            req_path = os.path.join(temp_dir, "requirements.txt")
            with open(req_path, "w") as f:
                f.write("requests==2.31.0\npydantic==2.5.0\n")
            
            # Create some Python files
            main_path = os.path.join(temp_dir, "main.py")
            with open(main_path, "w") as f:
                f.write("# Test plugin main file\n")
                f.write("def main():\n    print('Hello from test plugin')\n")
            
            # Add some bulk data if requested
            if size_mb > 1:
                data_path = os.path.join(temp_dir, "data.bin")
                with open(data_path, "wb") as f:
                    f.write(os.urandom(size_mb * 1024 * 1024))
            
            # Create zip file
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arc_name)
        
        return path
    
    @staticmethod
    def generate_task_data(task_type: str = "url", **kwargs) -> Dict:
        """Generate task data for testing."""
        base_data = {
            "platform": kwargs.get("platform", "manylinux2014_x86_64"),
            "suffix": kwargs.get("suffix", "offline")
        }
        
        if task_type == "url":
            base_data["url"] = kwargs.get("url", "https://example.com/test-plugin.difypkg")
        elif task_type == "marketplace":
            base_data.update({
                "author": kwargs.get("author", "test-author"),
                "name": kwargs.get("name", "test-plugin"),
                "version": kwargs.get("version", "1.0.0")
            })
        
        return base_data


class PerformanceMonitor:
    """Monitor performance during integration tests."""
    
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def measure(self, operation: str):
        """Measure time for an operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            logger.info(f"{operation} took {duration:.2f}s")
    
    def get_stats(self, operation: str) -> Dict:
        """Get statistics for an operation."""
        if operation not in self.metrics:
            return {}
        
        times = self.metrics[operation]
        return {
            "count": len(times),
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "total": sum(times)
        }
    
    def report(self):
        """Generate performance report."""
        report = []
        for operation, times in self.metrics.items():
            stats = self.get_stats(operation)
            report.append(f"{operation}: {stats}")
        return "\n".join(report)


class ChaosMonkey:
    """Introduce controlled chaos for resilience testing."""
    
    def __init__(self, orchestrator: ServiceOrchestrator):
        self.orchestrator = orchestrator
    
    async def kill_random_worker(self):
        """Kill a random Celery worker."""
        containers = self.orchestrator.docker_client.containers.list(
            filters={"label": f"com.docker.compose.project={self.orchestrator.project_name}"}
        )
        
        workers = [c for c in containers if "worker" in c.name]
        if workers:
            import random
            victim = random.choice(workers)
            logger.warning(f"Chaos Monkey killing worker: {victim.name}")
            victim.kill()
    
    async def introduce_network_delay(self, service: str, delay_ms: int):
        """Add network delay to a service."""
        containers = self.orchestrator.docker_client.containers.list(
            filters={"label": f"com.docker.compose.service={service}"}
        )
        
        for container in containers:
            # Add network delay using tc (traffic control)
            container.exec_run(
                f"tc qdisc add dev eth0 root netem delay {delay_ms}ms",
                privileged=True
            )
            logger.warning(f"Added {delay_ms}ms delay to {container.name}")
    
    async def fill_disk_space(self, service: str, size_mb: int):
        """Fill disk space in a service container."""
        containers = self.orchestrator.docker_client.containers.list(
            filters={"label": f"com.docker.compose.service={service}"}
        )
        
        for container in containers:
            # Create a large file
            container.exec_run(f"dd if=/dev/zero of=/tmp/bigfile bs=1M count={size_mb}")
            logger.warning(f"Created {size_mb}MB file in {container.name}")


@contextmanager
def integration_test_environment(compose_file: str = "docker-compose.test.yml"):
    """Context manager for integration test environment."""
    orchestrator = ServiceOrchestrator(compose_file)
    
    try:
        # Start services
        orchestrator.start_services()
        
        # Wait for services to be healthy
        health_checks = HealthChecks()
        orchestrator.wait_for_service("redis", health_checks.check_redis)
        
        # Async health checks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            orchestrator.wait_for_service("backend", health_checks.check_backend)
        )
        
        yield orchestrator
        
    finally:
        # Always stop services
        orchestrator.stop_services()
        if loop:
            loop.close()