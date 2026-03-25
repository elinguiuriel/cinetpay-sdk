"""Exception hierarchy used across the CinetPay SDK.

The client normalizes transport failures and CinetPay API failures into a small
set of exception types so application code can react without inspecting raw HTTP
details everywhere.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class CinetPayError(Exception):
    """Base class for all SDK exceptions.

    The additional attributes mirror the metadata frequently returned by the
    CinetPay API and allow callers to inspect machine-readable error details
    without parsing error messages.
    """

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
    """Raised when CinetPay responds but rejects the request."""


class AuthenticationError(APIError):
    """Raised when credentials or access tokens are rejected by CinetPay."""


class ValidationError(APIError):
    """Raised when the local payload or API parameters are considered invalid."""


class NetworkError(CinetPayError):
    """Raised when the SDK cannot reach the CinetPay API endpoint."""
