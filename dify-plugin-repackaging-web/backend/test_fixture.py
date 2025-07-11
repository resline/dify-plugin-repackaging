"""Test that the async_client fixture works"""
import pytest

@pytest.mark.asyncio
async def test_async_client_fixture(async_client):
    """Test that async_client fixture can make requests"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"