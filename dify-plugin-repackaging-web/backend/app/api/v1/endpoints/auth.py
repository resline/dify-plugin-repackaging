"""Browser session endpoints for password authentication."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    auth_rate_limiter,
    create_session_token,
    get_client_identifier,
    verify_password,
    verify_session_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=4096)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    client_id = get_client_identifier(request)
    if auth_rate_limiter.is_rate_limited(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Please try again later.",
            headers={"Retry-After": "60"},
        )
    if not verify_password(payload.password):
        auth_rate_limiter.record_attempt(client_id)
        raise HTTPException(status_code=401, detail="Invalid password")

    auth_rate_limiter.reset(client_id)
    forwarded_protocol = request.headers.get("x-forwarded-proto", request.url.scheme)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=forwarded_protocol == "https",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@router.get("/session")
async def session(request: Request) -> dict:
    authentication_required = bool(settings.AUTH_PASSWORD)
    return {
        "authentication_required": authentication_required,
        "authenticated": (
            not authentication_required
            or verify_session_token(request.cookies.get(SESSION_COOKIE_NAME))
        ),
    }


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False}
