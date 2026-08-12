"""Focused tests for the static FileManager service."""

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from app.services.file_manager import FileManager


def completed_task(task_id: str, filename: str = "plugin.difypkg") -> str:
    return json.dumps(
        {
            "task_id": task_id,
            "status": "completed",
            "output_filename": filename,
            "created_at": "2026-08-12T10:00:00+00:00",
            "completed_at": "2026-08-12T10:01:00+00:00",
        }
    )


def test_get_file_info_for_completed_file(temp_directory):
    task_id = "task-1"
    task_dir = os.path.join(temp_directory, task_id)
    os.makedirs(task_dir)
    file_path = os.path.join(task_dir, "plugin.difypkg")
    with open(file_path, "wb") as output:
        output.write(b"package")

    redis = Mock()
    redis.get.return_value = completed_task(task_id)
    with (
        patch("app.services.file_manager.redis_client", redis),
        patch("app.services.file_manager.settings.TEMP_DIR", temp_directory),
    ):
        result = FileManager.get_file_info(task_id)

    assert result is not None
    assert result["file_id"] == task_id
    assert result["size"] == 7
    assert result["download_url"].endswith(f"/{task_id}/download")


def test_get_file_info_rejects_missing_or_incomplete_task():
    redis = Mock()
    redis.get.return_value = None
    with patch("app.services.file_manager.redis_client", redis):
        assert FileManager.get_file_info("missing") is None

    redis.get.return_value = json.dumps({"task_id": "pending", "status": "processing"})
    with patch("app.services.file_manager.redis_client", redis):
        assert FileManager.get_file_info("pending") is None


def test_get_file_path_uses_validated_task_directory(temp_directory):
    task_id = "task-2"
    task_dir = os.path.join(temp_directory, task_id)
    os.makedirs(task_dir)
    file_path = os.path.join(task_dir, "plugin.difypkg")
    with open(file_path, "wb") as output:
        output.write(b"package")

    with (
        patch.object(
            FileManager,
            "get_file_info",
            return_value={"filename": "plugin.difypkg"},
        ),
        patch("app.services.file_manager.settings.TEMP_DIR", temp_directory),
    ):
        assert FileManager.get_file_path(task_id) == file_path


def test_list_completed_files_sorts_and_paginates():
    redis = Mock()
    redis.scan_iter.return_value = ["task:old", "task:new", "task:pending"]
    redis.get.side_effect = lambda key: {
        "task:old": completed_task("old"),
        "task:new": completed_task("new"),
        "task:pending": json.dumps({"task_id": "pending", "status": "processing"}),
    }[key]
    file_info = {
        "old": {"file_id": "old", "created_at": "2026-08-10T00:00:00Z"},
        "new": {"file_id": "new", "created_at": "2026-08-12T00:00:00Z"},
    }

    with (
        patch("app.services.file_manager.redis_client", redis),
        patch.object(FileManager, "get_file_info", side_effect=lambda task_id: file_info[task_id]),
    ):
        result = FileManager.list_completed_files(limit=1, offset=0)

    assert result["total"] == 2
    assert result["has_more"] is True
    assert result["files"][0]["file_id"] == "new"


def test_delete_file_removes_directory_and_redis_record(temp_directory):
    task_id = "task-3"
    task_dir = os.path.join(temp_directory, task_id)
    os.makedirs(task_dir)
    redis = Mock()
    redis.get.return_value = completed_task(task_id)

    with (
        patch("app.services.file_manager.redis_client", redis),
        patch("app.services.file_manager.settings.TEMP_DIR", temp_directory),
    ):
        assert FileManager.delete_file(task_id) is True

    assert not os.path.exists(task_dir)
    redis.delete.assert_called_once_with(f"task:{task_id}")


def test_delete_file_returns_false_for_unknown_task():
    redis = Mock()
    redis.get.return_value = None
    with patch("app.services.file_manager.redis_client", redis):
        assert FileManager.delete_file("missing") is False


def test_get_storage_stats_reads_real_files(temp_directory):
    os.makedirs(os.path.join(temp_directory, "task"))
    with open(os.path.join(temp_directory, "task", "one.difypkg"), "wb") as output:
        output.write(b"1234")
    with open(os.path.join(temp_directory, "task", "two.difypkg"), "wb") as output:
        output.write(b"56")

    with patch("app.services.file_manager.settings.TEMP_DIR", temp_directory):
        result = FileManager.get_storage_stats()

    assert result["total_size"] == 6
    assert result["file_count"] == 2
    assert result["directory_count"] == 1


def test_cleanup_old_files_removes_completed_and_orphaned_directories(temp_directory):
    completed_dir = os.path.join(temp_directory, "completed")
    active_dir = os.path.join(temp_directory, "active")
    orphan_dir = os.path.join(temp_directory, "orphan")
    for directory in (completed_dir, active_dir, orphan_dir):
        os.makedirs(directory)
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
        os.utime(directory, (old_time, old_time))

    redis = Mock()
    redis.get.side_effect = lambda key: {
        "task:completed": json.dumps({"status": "completed"}),
        "task:active": json.dumps({"status": "processing"}),
        "task:orphan": None,
    }[key]

    with (
        patch("app.services.file_manager.redis_client", redis),
        patch("app.services.file_manager.settings.TEMP_DIR", temp_directory),
    ):
        assert FileManager.cleanup_old_files(retention_days=5) == 2

    assert not os.path.exists(completed_dir)
    assert os.path.exists(active_dir)
    assert not os.path.exists(orphan_dir)
    redis.delete.assert_called_once_with("task:completed")
