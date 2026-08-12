"""Tests for the current streaming download service contract."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.core.config import settings
from app.services.download import DownloadService


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *_args):
        return False


@pytest.fixture
def allowed_domains(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOWNLOAD_DOMAINS",
        ["github.com", "marketplace.dify.ai", "example.com"],
    )


def test_validate_url_accepts_http_and_subdomains(allowed_domains):
    assert DownloadService.validate_url("https://github.com/a/plugin.difypkg")
    assert DownloadService.validate_url("http://www.github.com/a/plugin.difypkg")
    assert DownloadService.validate_url("https://cdn.example.com/plugin.difypkg")


@pytest.mark.parametrize(
    "url",
    [
        "https://malicious.example/plugin.difypkg",
        "https://github.evil.example/plugin.difypkg",
        "https://evilgithub.com/plugin.difypkg",
        "ftp://github.com/plugin.difypkg",
        "not-a-url",
    ],
)
def test_validate_url_rejects_unsafe_urls(url, allowed_domains):
    assert DownloadService.validate_url(url) is False


@pytest.mark.asyncio
async def test_check_file_size_reads_content_length():
    response = Mock(headers={"content-length": "4096"})
    response.raise_for_status = Mock()
    client = Mock()
    client.head = AsyncMock(return_value=response)

    with patch("app.services.download.get_async_client", return_value=AsyncContext(client)):
        assert await DownloadService.check_file_size("https://example.com/plugin.difypkg") == 4096


@pytest.mark.asyncio
async def test_check_file_size_returns_none_when_unknown_or_unavailable():
    response = Mock(headers={})
    response.raise_for_status = Mock()
    client = Mock()
    client.head = AsyncMock(return_value=response)

    with patch("app.services.download.get_async_client", return_value=AsyncContext(client)):
        assert await DownloadService.check_file_size("https://example.com/plugin.difypkg") is None

    client.head = AsyncMock(side_effect=httpx.ConnectError("offline"))
    with patch("app.services.download.get_async_client", return_value=AsyncContext(client)):
        assert await DownloadService.check_file_size("https://example.com/plugin.difypkg") is None


@pytest.mark.asyncio
async def test_download_file_streams_to_task_directory(temp_directory, allowed_domains):
    content = b"PK\x03\x04plugin"

    async def chunks(**_kwargs):
        yield content[:4]
        yield content[4:]

    response = Mock(headers={"content-length": str(len(content))}, status_code=200)
    response.raise_for_status = Mock()
    response.aiter_bytes = Mock(side_effect=chunks)
    client = Mock()
    client.stream = Mock(return_value=AsyncContext(response))

    with (
        patch.object(DownloadService, "check_file_size", new=AsyncMock(return_value=len(content))),
        patch("app.services.download.get_async_client", return_value=AsyncContext(client)),
        patch("app.services.download.settings.TEMP_DIR", temp_directory),
    ):
        file_path, filename = await DownloadService.download_file(
            "https://example.com/plugin.difypkg", "task-1"
        )

    assert filename == "plugin.difypkg"
    with open(file_path, "rb") as downloaded:
        assert downloaded.read() == content


@pytest.mark.asyncio
async def test_download_file_builds_marketplace_filename(temp_directory, allowed_domains):
    async def chunks(**_kwargs):
        yield b"package"

    response = Mock(headers={}, status_code=200)
    response.raise_for_status = Mock()
    response.aiter_bytes = Mock(side_effect=chunks)
    client = Mock()
    client.stream = Mock(return_value=AsyncContext(response))

    with (
        patch.object(DownloadService, "check_file_size", new=AsyncMock(return_value=None)),
        patch("app.services.download.get_async_client", return_value=AsyncContext(client)),
        patch("app.services.download.settings.TEMP_DIR", temp_directory),
    ):
        _, filename = await DownloadService.download_file(
            "https://marketplace.dify.ai/api/v1/plugins/lfenghx/json2chart/1.2.0/download",
            "task-2",
        )

    assert filename == "lfenghx_json2chart_1.2.0.difypkg"


@pytest.mark.asyncio
async def test_download_file_rejects_invalid_source_and_extension(allowed_domains):
    with pytest.raises(ValueError, match="domain not allowed"):
        await DownloadService.download_file(
            "https://evil.example/plugin.difypkg", "task-3"
        )

    with pytest.raises(ValueError, match="must point to a .difypkg"):
        await DownloadService.download_file("https://example.com/plugin.zip", "task-3")


@pytest.mark.asyncio
async def test_download_file_enforces_size_before_and_during_stream(temp_directory, allowed_domains):
    url = "https://example.com/plugin.difypkg"
    with patch.object(
        DownloadService,
        "check_file_size",
        new=AsyncMock(return_value=settings.MAX_FILE_SIZE + 1),
    ):
        with pytest.raises(ValueError, match="File too large"):
            await DownloadService.download_file(url, "task-4")

    response = Mock(
        headers={"content-length": str(settings.MAX_FILE_SIZE + 1)},
        status_code=200,
    )
    response.raise_for_status = Mock()
    client = Mock()
    client.stream = Mock(return_value=AsyncContext(response))
    with (
        patch.object(DownloadService, "check_file_size", new=AsyncMock(return_value=None)),
        patch("app.services.download.get_async_client", return_value=AsyncContext(client)),
        patch("app.services.download.settings.TEMP_DIR", temp_directory),
    ):
        with pytest.raises(ValueError, match="File too large"):
            await DownloadService.download_file(url, "task-4")


@pytest.mark.asyncio
async def test_download_file_retries_transient_connection_errors(temp_directory, allowed_domains):
    client = Mock()
    client.stream = Mock(side_effect=httpx.ConnectError("offline"))

    with (
        patch.object(DownloadService, "check_file_size", new=AsyncMock(return_value=None)),
        patch("app.services.download.get_async_client", return_value=AsyncContext(client)),
        patch("app.services.download.asyncio.sleep", new=AsyncMock()) as sleep,
        patch("app.services.download.settings.TEMP_DIR", temp_directory),
    ):
        with pytest.raises(httpx.ConnectError):
            await DownloadService.download_file(
                "https://example.com/plugin.difypkg", "task-5"
            )

    assert client.stream.call_count == 3
    assert sleep.await_count == 2
