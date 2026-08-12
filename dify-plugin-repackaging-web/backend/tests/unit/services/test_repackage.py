"""Behavior tests for repackaging retries and output discovery."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.config import settings
from app.services.repackage import RepackageService


def process_with(lines, returncode=0):
    process = MagicMock()
    process.returncode = returncode
    process.stdout = MagicMock()
    process.stdout.readline = AsyncMock(side_effect=lines)
    process.wait = AsyncMock(return_value=returncode)
    process.terminate = Mock()
    process.kill = Mock()
    return process


@pytest.mark.asyncio
async def test_repackage_plugin_moves_output_and_reports_completion(tmp_path):
    source = tmp_path / "plugin.difypkg"
    source.write_bytes(b"source")
    output = tmp_path / "plugin-offline.difypkg"
    output.write_bytes(b"result")
    process = process_with([b"Unziping ...\n", b"Repackage success.\n", b""])

    with (
        patch.object(settings, "SCRIPTS_DIR", str(tmp_path)),
        patch.object(settings, "TEMP_DIR", str(tmp_path / "tasks")),
        patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)) as spawn,
    ):
        updates = [
            update
            async for update in RepackageService.repackage_plugin(
                str(source), "manylinux2014_x86_64", "offline", "task-1"
            )
        ]

    assert updates[-1] == ("Output file: plugin-offline.difypkg", 100)
    assert (tmp_path / "tasks" / "task-1" / output.name).read_bytes() == b"result"
    command = spawn.await_args.args
    assert command[0].endswith("plugin_repackaging.sh")
    assert command[1:3] == ("-p", "manylinux2014_x86_64")


@pytest.mark.asyncio
async def test_repackage_plugin_retries_failed_exit_code(tmp_path):
    source = tmp_path / "plugin.difypkg"
    source.write_bytes(b"source")
    output = tmp_path / "plugin-offline.difypkg"
    output.write_bytes(b"result")
    failed = process_with([b"network error\n", b""], returncode=1)
    succeeded = process_with([b"Repackage success.\n", b""], returncode=0)

    with (
        patch.object(settings, "SCRIPTS_DIR", str(tmp_path)),
        patch.object(settings, "TEMP_DIR", str(tmp_path / "tasks")),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=[failed, succeeded]),
        ) as spawn,
        patch("app.services.repackage.asyncio.sleep", new=AsyncMock()) as sleep,
    ):
        updates = [
            update
            async for update in RepackageService.repackage_plugin(
                str(source), "", "offline", "task-2"
            )
        ]

    assert updates[-1][1] == 100
    assert spawn.await_count == 2
    sleep.assert_awaited_once_with(2.0)


@pytest.mark.asyncio
async def test_repackage_plugin_raises_after_three_failures(tmp_path):
    source = tmp_path / "plugin.difypkg"
    source.write_bytes(b"source")
    processes = [process_with([b"failed\n", b""], returncode=1) for _ in range(3)]

    with (
        patch.object(settings, "SCRIPTS_DIR", str(tmp_path)),
        patch.object(settings, "TEMP_DIR", str(tmp_path / "tasks")),
        patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=processes)) as spawn,
        patch("app.services.repackage.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(RuntimeError, match="exit code 1"):
            async for _ in RepackageService.repackage_plugin(
                str(source), "", "offline", "task-3"
            ):
                pass

    assert spawn.await_count == 3


def test_find_output_file_prefers_expected_name_then_suffix(tmp_path):
    expected = tmp_path / "plugin-offline.difypkg"
    expected.write_bytes(b"expected")
    fallback = tmp_path / "another-offline.difypkg"
    fallback.write_bytes(b"fallback")

    assert RepackageService._find_output_file(
        str(tmp_path), "plugin.difypkg", "offline"
    ) == expected.name
    expected.unlink()
    assert RepackageService._find_output_file(
        str(tmp_path), "plugin.difypkg", "offline"
    ) == fallback.name
    fallback.unlink()
    assert RepackageService._find_output_file(
        str(tmp_path), "plugin.difypkg", "offline"
    ) is None
