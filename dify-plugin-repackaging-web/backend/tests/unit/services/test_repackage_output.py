"""Regression tests for subprocess output handling during repackaging."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.config import settings
from app.services.repackage import RepackageService


def make_process(lines, returncode=0):
    """Build a subprocess mock that emits the supplied output lines."""
    process = MagicMock()
    process.returncode = returncode
    process.stdout = MagicMock()
    process.stdout.readline = AsyncMock(side_effect=lines)
    process.wait = AsyncMock(return_value=returncode)
    process.terminate = Mock()
    process.kill = Mock()
    return process


@pytest.mark.asyncio
async def test_non_utf8_subprocess_output_does_not_retry(tmp_path):
    """Keep processing logs containing bytes that are invalid UTF-8."""
    source_file = tmp_path / "json2chart.difypkg"
    source_file.write_bytes(b"package")
    output_file = tmp_path / "json2chart-offline.difypkg"
    output_file.write_bytes(b"offline package")
    process = make_process(
        [
            b"inflating: _assets/2.\xf5-chart.png\n",
            b"Repackage success.\n",
            b"",
        ]
    )
    subprocess_factory = AsyncMock(return_value=process)

    with (
        patch.object(settings, "SCRIPTS_DIR", str(tmp_path)),
        patch.object(settings, "TEMP_DIR", str(tmp_path / "tasks")),
        patch(
            "asyncio.create_subprocess_exec",
            new=subprocess_factory,
        ) as mock_exec,
    ):
        updates = [
            update
            async for update in RepackageService.repackage_plugin(
                str(source_file), "", "offline", "task-123"
            )
        ]

    assert mock_exec.await_count == 1
    assert any("\ufffd-chart.png" in message for message, _ in updates)
    assert (
        tmp_path / "tasks" / "task-123" / output_file.name
    ).read_bytes() == b"offline package"


@pytest.mark.asyncio
async def test_running_process_is_stopped_before_retry(tmp_path):
    """Terminate a live failed subprocess before starting its replacement."""
    source_file = tmp_path / "plugin.difypkg"
    source_file.write_bytes(b"package")
    output_file = tmp_path / "plugin-offline.difypkg"
    output_file.write_bytes(b"offline package")

    reader_error = RuntimeError("reader failed")
    first_process = make_process([reader_error], returncode=None)
    second_process = make_process(
        [b"Repackage success.\n", b""],
        returncode=0,
    )

    with (
        patch.object(settings, "SCRIPTS_DIR", str(tmp_path)),
        patch.object(settings, "TEMP_DIR", str(tmp_path / "tasks")),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=[first_process, second_process]),
        ) as mock_exec,
        patch("app.services.repackage.asyncio.sleep", new=AsyncMock()),
    ):
        updates = [
            update
            async for update in RepackageService.repackage_plugin(
                str(source_file), "", "offline", "task-456"
            )
        ]

    assert updates[-1] == ("Output file: plugin-offline.difypkg", 100)
    assert mock_exec.await_count == 2
    first_process.terminate.assert_called_once_with()
    first_process.wait.assert_awaited_once_with()
