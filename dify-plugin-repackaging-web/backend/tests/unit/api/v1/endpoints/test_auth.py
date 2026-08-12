import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import (
    SESSION_COOKIE_NAME,
    auth_rate_limiter,
    create_session_token,
    verify_session_token,
)


@pytest.fixture(autouse=True)
def configured_password(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_PASSWORD", "correct-password")
    auth_rate_limiter.attempts.clear()
    yield
    auth_rate_limiter.attempts.clear()


@pytest.mark.asyncio
async def test_login_sets_an_http_only_session_cookie(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    cookie = response.headers["set-cookie"]
    assert SESSION_COOKIE_NAME in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "correct-password" not in cookie

    session = await async_client.get("/api/v1/auth/session")
    assert session.json() == {
        "authentication_required": True,
        "authenticated": True,
    }


@pytest.mark.asyncio
async def test_login_rejects_an_invalid_password(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid password"
    assert SESSION_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_logout_clears_the_session(async_client):
    await async_client.post(
        "/api/v1/auth/login",
        json={"password": "correct-password"},
    )

    response = await async_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}

    session = await async_client.get("/api/v1/auth/session")
    assert session.json()["authenticated"] is False


def test_session_tokens_are_signed_and_expire():
    token = create_session_token()
    assert verify_session_token(token) is True
    assert verify_session_token(f"{token}tampered") is False
    assert verify_session_token(create_session_token(max_age=-1)) is False


def test_websocket_rejects_a_missing_session(test_client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with test_client.websocket_connect("/ws/tasks/task-without-session"):
            pass

    assert exc_info.value.code == 1008
