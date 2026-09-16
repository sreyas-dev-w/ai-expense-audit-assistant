"""Session tokens and the request-scoped identity dependencies.

Tokens are ``<payload>.<signature>`` where the payload is url-safe base64 of
``employee_id:expiry`` and the signature is an HMAC-SHA256 over that payload
keyed with ``AUTH_SECRET_KEY``. This keeps sign-in self-contained (no session
table, no extra dependency) while still making the token unforgeable by a
client.

Credentials themselves are compared in ``app/services/auth_service.py``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.models.employees import Employee
from app.repositories.employee_repository import EmployeeRepository

_SEPARATOR = "."


class InvalidTokenError(Exception):
    """Raised when a token is malformed, tampered with, or expired."""


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _b64encode(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _b64decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode("utf-8")


def create_access_token(employee_id: str) -> tuple[str, int]:
    """Return ``(token, ttl_seconds)`` for the given employee."""
    ttl = settings.auth_token_ttl_seconds
    payload = _b64encode(f"{employee_id}:{int(time.time()) + ttl}")
    return f"{payload}{_SEPARATOR}{_sign(payload)}", ttl


def read_access_token(token: str) -> str:
    """Return the employee id carried by a valid token."""
    payload, _, signature = token.partition(_SEPARATOR)
    if not payload or not signature:
        raise InvalidTokenError("Malformed token")
    if not hmac.compare_digest(signature, _sign(payload)):
        raise InvalidTokenError("Token signature does not match")
    try:
        employee_id, _, expiry = _b64decode(payload).rpartition(":")
        expires_at = int(expiry)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as exc:
        raise InvalidTokenError("Token payload is not readable") from exc
    if not employee_id:
        raise InvalidTokenError("Token payload is missing a subject")
    if expires_at < int(time.time()):
        raise InvalidTokenError("Token has expired")
    return employee_id


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


async def get_current_employee(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Employee:
    try:
        employee_id = read_access_token(_bearer_token(request))
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    employee = await EmployeeRepository(session).get_employee_model(employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return employee


async def require_manager(
    employee: Employee = Depends(get_current_employee),
) -> Employee:
    if not employee.is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to managers",
        )
    return employee
