"""
Locust performance testing configuration for Dify Plugin Repackaging Application
"""
from locust import HttpUser, task, between, events
from locust.exception import LocustError
import random
import os
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data
SAMPLE_FILES = {
    "small": {"path": "test_files/sample_1mb.difypkg", "size": 1048576},
    "medium": {"path": "test_files/sample_10mb.difypkg", "size": 10485760},
    "large": {"path": "test_files/sample_50mb.difypkg", "size": 52428800},
}

MARKETPLACE_PLUGINS = [
    {"author": "langgenius", "name": "agent", "version": "0.0.9"},
    {"author": "langgenius", "name": "ollama", "version": "0.1.0"},
    {"author": "antv", "name": "visualization", "version": "0.1.7"},
]

PLATFORMS = [
    "manylinux2014_x86_64",
    "manylinux2014_aarch64",
    "manylinux_2_17_x86_64",
    "manylinux_2_17_aarch64",
]

class DifyRepackagingUser(HttpUser):
    wait_time = between(5, 10)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_ids = []
        self.completed_files = []
        self.ws_connections = []
    
    def on_start(self):
        """Initialize user session"""
        logger.info(f"User {self.client.base_url} starting session")
        
        # Check health endpoint
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")
                raise LocustError("Service unhealthy")
    
    @task(40)
    def upload_file(self):
        """Test file upload with various file sizes"""
        file_type = random.choice(["small", "medium", "large"])
        file_info = SAMPLE_FILES[file_type]
        
        # Create test file if it doesn't exist
        if not os.path.exists(file_info["path"]):
            os.makedirs(os.path.dirname(file_info["path"]), exist_ok=True)
            with open(file_info["path"], "wb") as f:
                f.write(b"DIFYPKG" + b"\x00" * (file_info["size"] - 7))
        
        platform = random.choice(PLATFORMS)
        suffix = random.choice(["offline", "bundled", "packaged"])
        
        with open(file_info["path"], "rb") as f:
            files = {"file": (os.path.basename(file_info["path"]), f, "application/octet-stream")}
            data = {"platform": platform, "suffix": suffix}
            
            start_time = time.time()
            with self.client.post(
                "/api/v1/tasks/upload",
                files=files,
                data=data,
                catch_response=True,
                name=f"/api/v1/tasks/upload [{file_type}]"
            ) as response:
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    task_data = response.json()
                    self.task_ids.append(task_data["task_id"])
                    
                    # Log performance metrics
                    logger.info(
                        f"File upload successful: {file_type} ({file_info['size']/1048576:.1f}MB) "
                        f"in {elapsed_time:.2f}s ({file_info['size']/elapsed_time/1048576:.1f}MB/s)"
                    )
                    response.success()
                else:
                    response.failure(f"Upload failed: {response.status_code} - {response.text}")
    
    @task(30)
    def create_marketplace_task(self):
        """Test marketplace plugin repackaging"""
        plugin = random.choice(MARKETPLACE_PLUGINS)
        platform = random.choice(PLATFORMS)
        
        payload = {
            "marketplace_plugin": plugin,
            "platform": platform,
            "suffix": "offline"
        }
        
        with self.client.post(
            "/api/v1/tasks",
            json=payload,
            catch_response=True,
            name="/api/v1/tasks [marketplace]"
        ) as response:
            if response.status_code == 200:
                task_data = response.json()
                self.task_ids.append(task_data["task_id"])
                response.success()
            else:
                response.failure(f"Marketplace task failed: {response.status_code}")
    
    @task(20)
    def download_file(self):
        """Test file download"""
        if not self.completed_files:
            # Try to get completed files list
            with self.client.get("/api/v1/files?limit=10", catch_response=True) as response:
                if response.status_code == 200:
                    files_data = response.json()
                    self.completed_files = [f["file_id"] for f in files_data.get("files", [])]
        
        if self.completed_files:
            file_id = random.choice(self.completed_files)
            
            with self.client.get(
                f"/api/v1/files/{file_id}/download",
                catch_response=True,
                stream=True,
                name="/api/v1/files/{file_id}/download"
            ) as response:
                if response.status_code == 200:
                    # Stream the download to avoid memory issues
                    total_size = 0
                    start_time = time.time()
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        total_size += len(chunk)
                    
                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"Download successful: {total_size/1048576:.1f}MB "
                        f"in {elapsed_time:.2f}s ({total_size/elapsed_time/1048576:.1f}MB/s)"
                    )
                    response.success()
                else:
                    response.failure(f"Download failed: {response.status_code}")
    
    @task(10)
    def list_files(self):
        """Test file listing with pagination"""
        limit = random.choice([10, 50, 100])
        offset = random.randint(0, 100)
        
        with self.client.get(
            f"/api/v1/files?limit={limit}&offset={offset}",
            catch_response=True,
            name="/api/v1/files"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                file_count = len(data.get("files", []))
                logger.info(f"Listed {file_count} files")
                response.success()
            else:
                response.failure(f"File listing failed: {response.status_code}")
    
    @task(5)
    def check_task_status(self):
        """Check status of created tasks"""
        if self.task_ids:
            task_id = random.choice(self.task_ids)
            
            with self.client.get(
                f"/api/v1/tasks/{task_id}",
                catch_response=True,
                name="/api/v1/tasks/{task_id}"
            ) as response:
                if response.status_code == 200:
                    task_data = response.json()
                    if task_data["status"] == "completed":
                        # Add to completed files for download testing
                        self.completed_files.append(task_id)
                    response.success()
                else:
                    response.failure(f"Task status check failed: {response.status_code}")
    
    def on_stop(self):
        """Clean up user session"""
        logger.info(f"User session ending. Created {len(self.task_ids)} tasks")


class WebSocketUser(HttpUser):
    """Separate user class for WebSocket testing"""
    wait_time = between(30, 60)
    
    @task
    def connect_websocket(self):
        """Test WebSocket connections"""
        # Note: Locust doesn't have built-in WebSocket support
        # This is a placeholder for WebSocket testing logic
        # In practice, you'd use a separate WebSocket testing tool
        pass


# Event hooks for performance monitoring
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Log slow requests"""
    if response_time > 5000:  # Log requests taking more than 5 seconds
        logger.warning(
            f"Slow request: {request_type} {name} took {response_time}ms "
            f"(size: {response_length} bytes, status: {response.status_code if response else 'N/A'})"
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment"""
    logger.info(f"Load test starting with {environment.parsed_options.num_users} users")
    
    # Create test files directory
    os.makedirs("test_files", exist_ok=True)
    
    # Log test configuration
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Reset stats: {environment.reset_stats}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate test summary"""
    logger.info("Load test completed")
    
    # Calculate and log key metrics
    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    
    if total_requests > 0:
        failure_rate = (total_failures / total_requests) * 100
        logger.info(f"Total requests: {total_requests}")
        logger.info(f"Total failures: {total_failures} ({failure_rate:.2f}%)")
        logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
        logger.info(f"Median response time: {stats.total.median_response_time:.2f}ms")
        logger.info(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        logger.info(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")


# Custom shapes for different test scenarios
class StagesShape:
    """
    Load test with multiple stages:
    1. Ramp up to normal load
    2. Hold steady state
    3. Spike to peak load
    4. Return to normal
    5. Ramp down
    """
    stages = [
        {"duration": 300, "users": 100},    # Ramp up - 5 min
        {"duration": 1200, "users": 100},   # Steady state - 20 min
        {"duration": 300, "users": 500},    # Spike - 5 min
        {"duration": 600, "users": 500},    # Peak load - 10 min
        {"duration": 300, "users": 100},    # Return to normal - 5 min
        {"duration": 600, "users": 100},    # Steady state - 10 min
        {"duration": 300, "users": 0},      # Ramp down - 5 min
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["users"])
                return tick_data
            else:
                run_time -= stage["duration"]
        
        return None