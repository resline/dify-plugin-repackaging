"""
Unit tests for repackage service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import os
from pathlib import Path

from app.services.repackage import RepackageService
from app.core.config import settings


class TestRepackageService:
    """Test cases for RepackageService."""
    
    @pytest.fixture
    def repackage_service(self):
        """Create a RepackageService instance."""
        return RepackageService()
    
    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for testing."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.stdout = MagicMock()
            mock_process.stderr = MagicMock()
            mock_process.returncode = 0
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process
            yield mock_exec, mock_process
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_success(self, repackage_service, mock_subprocess, temp_directory):
        """Test successful plugin repackaging."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        file_path = f"{temp_directory}/test_plugin.difypkg"
        platform = "manylinux2014_x86_64"
        suffix = "offline"
        task_id = "test-task-123"
        
        # Mock stdout output
        output_lines = [
            b"Starting repackaging...\n",
            b"[INFO] Extracting plugin...\n",
            b"[INFO] Downloading dependencies...\n",
            b"[INFO] Creating offline package...\n",
            b"[SUCCESS] Output file: test_plugin-offline.difypkg\n"
        ]
        
        async def mock_readline():
            for line in output_lines:
                yield line
        
        mock_process.stdout.readline = AsyncMock(side_effect=output_lines)
        mock_process.stdout.__aiter__.return_value = output_lines
        
        # Act
        messages = []
        async for message, progress in repackage_service.repackage_plugin(
            file_path, platform, suffix, task_id
        ):
            messages.append((message, progress))
        
        # Assert
        assert len(messages) > 0
        assert any("Starting repackaging" in msg for msg, _ in messages)
        assert messages[-1][1] == 100  # Final progress should be 100%
        
        # Verify command was called correctly
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args[0]
        assert call_args[0].endswith("plugin_repackaging.sh")
        assert "-p" in call_args
        assert platform in call_args
        assert "-s" in call_args
        assert suffix in call_args
        assert "local" in call_args
        assert file_path in call_args
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_with_retry(self, repackage_service, mock_subprocess):
        """Test repackaging with retry on failure."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        file_path = "/tmp/test_plugin.difypkg"
        
        # First attempt fails, second succeeds
        mock_process.returncode = 1
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"Error: Network timeout\n",
            b""
        ])
        
        # Mock multiple attempts
        attempt_count = 0
        
        async def mock_exec_with_retry(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            
            process = AsyncMock()
            process.stdout = MagicMock()
            process.wait = AsyncMock()
            
            if attempt_count == 1:
                # First attempt fails
                process.returncode = 1
                process.stdout.readline = AsyncMock(side_effect=[
                    b"Error: Network timeout\n",
                    b""
                ])
            else:
                # Second attempt succeeds
                process.returncode = 0
                process.stdout.readline = AsyncMock(side_effect=[
                    b"[SUCCESS] Output file: test_plugin-offline.difypkg\n",
                    b""
                ])
            
            return process
        
        mock_exec.side_effect = mock_exec_with_retry
        
        # Act
        messages = []
        async for message, progress in repackage_service.repackage_plugin(
            file_path, "", "offline", "test-123"
        ):
            messages.append((message, progress))
        
        # Assert
        assert attempt_count >= 2  # Should have retried
        assert any("attempt 2" in msg for msg, _ in messages)
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_all_retries_fail(self, repackage_service, mock_subprocess):
        """Test repackaging when all retries fail."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        mock_process.returncode = 1
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        
        # Act
        messages = []
        with pytest.raises(Exception) as exc_info:
            async for message, progress in repackage_service.repackage_plugin(
                "/tmp/test.difypkg", "", "offline", "test-123"
            ):
                messages.append((message, progress))
        
        # Assert
        assert "All retry attempts failed" in str(exc_info.value)
        assert mock_exec.call_count == 3  # Max retries
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_progress_tracking(self, repackage_service, mock_subprocess):
        """Test progress tracking during repackaging."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        
        # Simulate progressive output
        output_lines = [
            b"[INFO] Starting process...\n",
            b"[INFO] Step 1 of 4: Extracting...\n",
            b"[INFO] Step 2 of 4: Analyzing...\n",
            b"[INFO] Step 3 of 4: Downloading...\n",
            b"[INFO] Step 4 of 4: Packaging...\n",
            b"[SUCCESS] Complete!\n"
        ]
        
        mock_process.stdout.readline = AsyncMock(side_effect=output_lines + [b""])
        
        # Act
        progress_values = []
        async for message, progress in repackage_service.repackage_plugin(
            "/tmp/test.difypkg", "", "offline", "test-123"
        ):
            progress_values.append(progress)
        
        # Assert
        assert len(progress_values) > 0
        assert progress_values[0] < progress_values[-1]  # Progress increases
        assert progress_values[-1] == 100  # Ends at 100%
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_marketplace(self, repackage_service, mock_subprocess):
        """Test repackaging marketplace plugin."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        author = "langgenius"
        name = "agent"
        version = "0.0.9"
        platform = "manylinux2014_x86_64"
        
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"[INFO] Downloading from marketplace...\n",
            b"[SUCCESS] Output file: agent-0.0.9-offline.difypkg\n",
            b""
        ])
        
        # Act
        messages = []
        async for message, progress in repackage_service.repackage_marketplace_plugin(
            author, name, version, platform, "offline", "test-123"
        ):
            messages.append((message, progress))
        
        # Assert
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args[0]
        assert "market" in call_args
        assert author in call_args
        assert name in call_args
        assert version in call_args
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_github(self, repackage_service, mock_subprocess):
        """Test repackaging GitHub release plugin."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        repo = "owner/repo"
        release = "v1.0.0"
        asset = "plugin.difypkg"
        
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"[INFO] Downloading from GitHub...\n",
            b"[SUCCESS] Output file: plugin-offline.difypkg\n",
            b""
        ])
        
        # Act
        messages = []
        async for message, progress in repackage_service.repackage_github_plugin(
            repo, release, asset, "", "offline", "test-123"
        ):
            messages.append((message, progress))
        
        # Assert
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args[0]
        assert "github" in call_args
        assert repo in call_args
        assert release in call_args
        assert asset in call_args
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_output_parsing(self, repackage_service, mock_subprocess):
        """Test parsing of output file from script output."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        expected_output = "test_plugin-0.1.0-offline.difypkg"
        
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"[INFO] Processing...\n",
            f"[SUCCESS] Output file: {expected_output}\n".encode(),
            b""
        ])
        
        # Act
        last_message = None
        async for message, progress in repackage_service.repackage_plugin(
            "/tmp/test.difypkg", "", "offline", "test-123"
        ):
            if "Output file:" in message:
                last_message = message
        
        # Assert
        assert last_message is not None
        assert expected_output in last_message
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_error_handling(self, repackage_service, mock_subprocess):
        """Test error handling during repackaging."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        
        # Simulate various error outputs
        error_outputs = [
            b"[ERROR] File not found: plugin.difypkg\n",
            b"[ERROR] Invalid plugin format\n",
            b"[ERROR] Network connection failed\n"
        ]
        
        for error_output in error_outputs:
            mock_process.returncode = 1
            mock_process.stdout.readline = AsyncMock(side_effect=[error_output, b""])
            
            # Act & Assert
            messages = []
            with pytest.raises(Exception):
                async for message, progress in repackage_service.repackage_plugin(
                    "/tmp/test.difypkg", "", "offline", "test-123"
                ):
                    messages.append(message)
            
            assert any("ERROR" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_repackage_plugin_timeout(self, repackage_service):
        """Test handling of process timeout."""
        # Arrange
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_process.stdout.readline = AsyncMock(
                side_effect=lambda: asyncio.sleep(10)  # Simulate hanging
            )
            mock_exec.return_value = mock_process
            
            # Act & Assert
            with pytest.raises(Exception):
                async for _ in repackage_service.repackage_plugin(
                    "/tmp/test.difypkg", "", "offline", "test-123"
                ):
                    pass


class TestRepackageServiceIntegration:
    """Integration tests for RepackageService."""
    
    @pytest.mark.asyncio
    async def test_concurrent_repackaging(self, repackage_service, mock_subprocess):
        """Test multiple concurrent repackaging operations."""
        # Arrange
        mock_exec, mock_process = mock_subprocess
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"[SUCCESS] Complete\n",
            b""
        ])
        
        # Act - Run 3 repackaging tasks concurrently
        tasks = []
        for i in range(3):
            task = repackage_service.repackage_plugin(
                f"/tmp/plugin_{i}.difypkg", "", "offline", f"task-{i}"
            )
            tasks.append([msg async for msg in task])
        
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 3
        assert mock_exec.call_count == 3