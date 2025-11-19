import os
import subprocess
import asyncio
import re
from typing import Tuple, AsyncGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RepackageService:
    # Security: Whitelist of allowed platforms for subprocess execution
    # These correspond to pip platform tags used in plugin_repackaging.sh
    ALLOWED_PLATFORMS = {
        "manylinux_2_17_x86_64",
        "manylinux_2_17_aarch64",
        "manylinux2014_x86_64",
        "manylinux2014_aarch64",
        "linux_x86_64",
        "linux_aarch64"
    }

    # Security: Regex pattern for validating suffix parameter
    # Only allow alphanumeric characters, hyphens, and underscores
    SUFFIX_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

    @staticmethod
    def _validate_platform(platform: str) -> None:
        """
        Validate platform parameter against whitelist to prevent command injection.

        Args:
            platform: Platform string to validate

        Raises:
            ValueError: If platform is not in the allowed whitelist

        Security: This prevents attackers from injecting shell commands via the -p flag
        """
        if platform and platform not in RepackageService.ALLOWED_PLATFORMS:
            logger.warning(f"Invalid platform attempted: {platform}")
            raise ValueError(
                f"Invalid platform '{platform}'. Allowed platforms: "
                f"{', '.join(sorted(RepackageService.ALLOWED_PLATFORMS))}"
            )

    @staticmethod
    def _validate_suffix(suffix: str) -> None:
        """
        Validate suffix parameter to prevent command injection.

        Args:
            suffix: Suffix string to validate

        Raises:
            ValueError: If suffix contains disallowed characters

        Security: This prevents attackers from injecting shell commands via the -s flag
        by restricting to alphanumeric, dash, and underscore characters only
        """
        if not suffix:
            raise ValueError("Suffix cannot be empty")

        if not RepackageService.SUFFIX_PATTERN.match(suffix):
            logger.warning(f"Invalid suffix attempted: {suffix}")
            raise ValueError(
                f"Invalid suffix '{suffix}'. Only alphanumeric characters, "
                f"hyphens, and underscores are allowed (pattern: ^[a-zA-Z0-9_-]+$)"
            )

    @staticmethod
    def _validate_file_path(file_path: str) -> None:
        """
        Validate file path to prevent path traversal attacks.

        Args:
            file_path: File path to validate

        Raises:
            ValueError: If file path contains suspicious patterns

        Security: This prevents path traversal attacks (../) and ensures the file
        is within the expected temporary directory
        """
        if not file_path:
            raise ValueError("File path cannot be empty")

        # Check for path traversal attempts
        if ".." in file_path:
            logger.warning(f"Path traversal attempted: {file_path}")
            raise ValueError("File path cannot contain '..' (path traversal not allowed)")

        # Normalize the path and check it's within allowed directory
        normalized_path = os.path.normpath(file_path)
        allowed_dir = os.path.normpath(settings.TEMP_DIR)

        # Ensure the file path is within the temp directory
        if not normalized_path.startswith(allowed_dir):
            logger.warning(f"File path outside temp directory: {file_path}")
            raise ValueError(f"File path must be within {settings.TEMP_DIR}")

        # Additional check: ensure file exists
        if not os.path.exists(normalized_path):
            logger.warning(f"File does not exist: {file_path}")
            raise ValueError(f"File does not exist: {file_path}")

    @staticmethod
    async def repackage_plugin(
        file_path: str, 
        platform: str, 
        suffix: str,
        task_id: str
    ) -> AsyncGenerator[Tuple[str, int], None]:
        """
        Run the repackaging script with retry logic and yield progress updates
        Returns generator of (message, progress_percentage)
        """
        # Security: Validate all user inputs before passing to subprocess
        RepackageService._validate_platform(platform)
        RepackageService._validate_suffix(suffix)
        RepackageService._validate_file_path(file_path)

        script_path = os.path.join(settings.SCRIPTS_DIR, "plugin_repackaging.sh")

        # Build command - all parameters are now validated
        cmd = [script_path]
        if platform:
            cmd.extend(["-p", platform])  # Safe: validated against whitelist
        cmd.extend(["-s", suffix, "local", file_path])  # Safe: validated with regex and path checks
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Retry logic parameters
        max_retries = 3
        base_delay = 2.0  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting repackaging (attempt {attempt + 1}/{max_retries})")
                
                # Run the script from the script's directory
                # This ensures output files are created in the expected location
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=settings.SCRIPTS_DIR
                )
                
                # Progress tracking
                progress_map = {
                    "Unziping": 20,
                    "Unzip success": 30,
                    "Repackaging": 40,
                    "Looking in indexes": 50,
                    "Collecting": 60,
                    "Successfully downloaded": 80,
                    "Repackage success": 100
                }
                
                current_progress = 10
                collected_output = []
                
                # Read output line by line
                while True:
                    try:
                        # Add timeout to prevent hanging
                        line = await asyncio.wait_for(process.stdout.readline(), timeout=300.0)
                    except asyncio.TimeoutError:
                        logger.error("Timeout waiting for script output")
                        process.terminate()
                        await process.wait()
                        raise RuntimeError("Repackaging timeout - process appears to be hanging")
                    
                    if not line:
                        break
                        
                    line_str = line.decode('utf-8').strip()
                    logger.info(f"Script output: {line_str}")
                    collected_output.append(line_str)
                    
                    # Update progress based on output
                    for key, progress in progress_map.items():
                        if key in line_str:
                            current_progress = progress
                            break
                    
                    yield (line_str, current_progress)
                
                # Wait for process to complete
                await process.wait()
                
                if process.returncode != 0:
                    error_msg = f"Repackaging failed with exit code {process.returncode}"
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"{error_msg}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Include collected output in error for debugging
                        full_error = f"{error_msg}\nScript output:\n" + "\n".join(collected_output[-20:])  # Last 20 lines
                        raise RuntimeError(full_error)
                
                # Find the output file in the scripts directory
                output_filename = RepackageService._find_output_file(
                    settings.SCRIPTS_DIR,
                    os.path.basename(file_path),
                    suffix
                )
                
                if not output_filename:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Output file not found. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise RuntimeError("Output file not found after repackaging")
                
                # Move the output file to the task directory
                source_path = os.path.join(settings.SCRIPTS_DIR, output_filename)
                task_dir = os.path.join(settings.TEMP_DIR, task_id)
                os.makedirs(task_dir, exist_ok=True)
                dest_path = os.path.join(task_dir, output_filename)
                
                # Move the file
                import shutil
                shutil.move(source_path, dest_path)
                logger.info(f"Moved output file from {source_path} to {dest_path}")
                
                yield (f"Output file: {output_filename}", 100)
                return  # Success, exit the retry loop
                
            except asyncio.CancelledError:
                # Handle cancellation gracefully
                if 'process' in locals():
                    process.terminate()
                    await process.wait()
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Repackaging error: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Repackaging failed after {max_retries} attempts: {e}")
                    raise
    
    @staticmethod
    def _find_output_file(directory: str, original_filename: str, suffix: str) -> str:
        """Find the repackaged output file"""
        base_name = original_filename.replace('.difypkg', '')
        expected_name = f"{base_name}-{suffix}.difypkg"
        
        output_path = os.path.join(directory, expected_name)
        if os.path.exists(output_path):
            return expected_name
        
        # Fallback: look for any file with suffix
        for file in os.listdir(directory):
            if file.endswith(f"-{suffix}.difypkg"):
                return file
        
        return None