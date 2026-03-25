"""Exceptions raised by the CinetPay SDK."""

from __future__ import annotations

from typing import Any, Dict, Optional


class CinetPayError(Exception):
    """Base SDK exception."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[int] = None,
        status: Optional[str] = None,
        http_status: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.http_status = http_status
        self.payload = payload or {}


class APIError(CinetPayError):
    """Raised when the API returns an error response."""


class AuthenticationError(APIError):
    """Raised when authentication fails or the token is invalid."""


class ValidationError(APIError):
    """Raised when the API rejects a request payload."""


class NetworkError(CinetPayError):
    """Raised when the SDK cannot reach the API."""
