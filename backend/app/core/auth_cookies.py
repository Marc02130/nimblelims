"""
P4 / S10: httpOnly access cookie + double-submit CSRF cookie helpers.
"""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Request, Response

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_COOKIE_NAME,
    COOKIE_PATH,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    CSRF_COOKIE_NAME,
)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def cookie_max_age_seconds() -> int:
    return int(ACCESS_TOKEN_EXPIRE_MINUTES) * 60


def set_auth_cookies(response: Response, access_token: str, csrf_token: Optional[str] = None) -> str:
    """
    Set nimble_access (httpOnly JWT) and nimble_csrf (readable double-submit).
    Returns the CSRF token value that was set.
    """
    csrf = csrf_token or new_csrf_token()
    max_age = cookie_max_age_seconds()
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=max_age,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite=COOKIE_SAMESITE,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf,
        max_age=max_age,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=False,
        samesite=COOKIE_SAMESITE,
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies."""
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite=COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=False,
        samesite=COOKIE_SAMESITE,
    )


def get_access_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(AUTH_COOKIE_NAME)


def get_csrf_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(CSRF_COOKIE_NAME)
