import os
import subprocess
import asyncio
from typing import Tuple, AsyncGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RepackageService:
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
        script_path = os.path.join(settings.SCRIPTS_DIR, "plugin_repackaging.sh")
        
        # Build command
        cmd = [script_path]
        if platform:
            cmd.extend(["-p", platform])
        cmd.extend(["-s", suffix, "local", file_path])
        
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